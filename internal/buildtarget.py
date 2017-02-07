# xpyBuild - eXtensible Python-based Build System
#
# This class is responsible for working out what tasks need to run, and for 
# scheduling them
#
# Copyright (c) 2013 - 2017 Software AG, Darmstadt, Germany and/or its licensors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# $Id: buildtarget.py 301527 2017-02-06 15:31:43Z matj $
#

import traceback, os, time
import difflib
from basetarget import BaseTarget
from buildcommon import *
from threading import Lock
from buildexceptions import BuildException
from utils.fileutils import deleteFile, mkdir, openForWrite, normLongPath, getmtime, exists, isfile, isdir

import logging
log = logging.getLogger('xpybuild.buildtarget')

class BuildTarget(object):
	"""
		Internal wrapper for a target which contains all the state needed during builds
	"""
	target = None
	depcount = 0
	isdirty = False
	lock = None
	_rdeps = None
	fdeps = None
	deps = None
	def __init__(self, target):
		"""
			Create a BuildTarget from a target. This target has an internal lock
			which is taken for some of the functions
		"""
		self.target = target
		self.lock = Lock()
		self._rdeps = []
		self.fdeps = []
		self.__implicitInputs = None

	def __hash__ (self): return hash(self.target) # delegate
	
	def __str__(self): return '%s'%self.target
	def __repr__(self): return 'BuildTarget.%s'%str(self)
	
	def __getattr__(self, name):
		if name == 'path': return self.target.path
		if name == 'options': return self.target.__options
		if name == 'name': return self.target.name
		if name == 'location': return self.target.location
		if name == 'priority': return -self.target.getPriority()
		if name == '_implicitInputsFile': return self.__getImplicitInputsFile()
		if name == 'stampfile': 
			if isDirPath(self.target.name):
				return self.__getImplicitInputsFile() # might as well re-use this for dirs
			else:
				return self.target.path
				
		raise AttributeError('Unknown attribute %s' % name)
	
	def setPriority(self, pri):
		self.target.priority(-pri)
	
	def __getImplicitInputsFile(self):
		x = self.target.workDir.replace('\\','/').split('/')
		# relies on basetarget._resolveTargetPath having been called
		return '/'.join(x[:-1])+'/implicit-inputs/'+x[-1]+'.txt' # since workDir is already unique (but don't contaminate work dir by putting this inside it)
	
	def __getImplicitInputs(self, context):
		# this is typically called in either uptodate or run, but never during dependency resolution 
		# since we don't have all our inputs yet at that point
		if self.__implicitInputs != None: return self.__implicitInputs

		# we could optimize this by not writing the file if all the 
		# dependencies are explicit i.e. no FindPathSets are present

		# sort the list in case of determinism problems with filesystem walk order
		x = sorted(self.resolveDependencies(context))
		
		# since this is meant to be a list of lines, normalize with a split->join
		# also make any non-linesep \r or \n chars explicit to avoid confusion when diffing
		x += [x.replace('\r','\\r').replace('\n','\\n') for x in os.linesep.join(self.target.getHashableImplicitInputs(context)).split(os.linesep)]
		
		self.__implicitInputs = x
		return x

	
	def resolveDependencies(self, context):
		"""
			Calls through to the wrapped target, which does the expansion/replacement
			of dependency strings here.
			
			Returns a list of dependencies as strings (paths). Either files or targets.
		"""
		if self.deps: return self.deps

		# note that some of these may be PathSetGeneratedByTarget path sets where 
		# the real list of dependencies is not yet known, and the target that 
		# will generate them is specified instead
		deps = self.target._resolveUnderlyingDependencies(context)
		
		deps = context._expandAtomicDeps(deps)

		if self.path in deps: deps.remove(self.path)
		
		self.deps = deps
		return self.deps
		
	def increment(self):
		"""
			Increments the number of outstanding dependencies to be built.
			Holds the object lock
		"""
		with self.lock:
			self.depcount = self.depcount + 1
	def decrement(self):
		"""
			Decrements the number of outstanding dependencies to be built
			and returns the new total.
			Holds the object lock
		"""
		depcount = 0;
		with self.lock:
			self.depcount = self.depcount - 1
			depcount = self.depcount
		return depcount
	def dirty(self):
		"""
			Marks the object as explicitly dirty to avoid doing uptodate checks
			Holds the object lock
			
			Returns the previous value of isdirty, i.e. True if this was a no-op. 
		"""
		with self.lock:
			r = self.isdirty
			self.isdirty = True
			return r
			
	def rdep(self, target):
		"""
			Adds a reverse dependency to this target
			Holds the object lock
		"""
		with self.lock:
			self._rdeps.append(target)
	def rdeps(self):
		"""
			Returns the list of reverse dependencies.
			Holds the object lock
		"""
		with self.lock:
			return self._rdeps
	def filedep(self, path):
		"""
			Adds to the list of file dependencies.
			Holds the object lock
		"""
		with self.lock:
			self.fdeps.append(path)
	def uptodate(self, context, ignoreDeps):
		"""
			Checks whether the target needs to be rebuilt.
			Returns true if the target is up to date and does not need a rebuild
			Holds the object lock
			
			Called during the main build phase, after the dependency resolution phase
		"""
		with self.lock:
			log.debug('Up-to-date check for %s', self.name)
			
			if self.isdirty: 
				# no need to log at info, will already have been done when it was marked dirty
				log.debug('Up-to-date check: %s has been marked dirty', self.name)
				return False

			if not exists(self.path):
				log.info('Up-to-date check: %s must be rebuilt because file does not exist: "%s"', self.name, self.path)
				self.isdirty = True # make sure we don't log this again
				return False
			
			if ignoreDeps: return True
			
			if not isfile(self.stampfile): # this is really an existence check, but if we have a dir it's an error so ignore
				# for directory targets
				log.info('Up-to-date check: %s must be rebuilt because stamp file does not exist: "%s"', self.name, self.stampfile)
				return False
			
			# assume that by this point our explicit dependencies at least exist, so it's safe to call getHashableImplicitDependencies
			implicitInputs = self.__getImplicitInputs(context)
			if implicitInputs or isDirPath(self.target.name):
				# this is to cope with targets that have implicit inputs (e.g. globbed pathsets); might as well use the same mechanism for directories (which need a stamp file anyway)
				if not exists(self._implicitInputsFile):
					log.info('Up-to-date check: %s must be rebuilt because implicit inputs/stamp file does not exist: "%s"', self.name, self._implicitInputsFile)
					return False
				iminpath = os.path.normpath(self._implicitInputsFile)
				iminpath = normLongPath(iminpath)
				with open(iminpath, 'rb') as f:
					latestImplicitInputs = f.read().split(os.linesep)
					if latestImplicitInputs != implicitInputs:
						thediff = list(difflib.unified_diff(latestImplicitInputs, implicitInputs,
							fromfile='inputs for previous build of the target (%d lines)'%len(implicitInputs),
							tofile='inputs for current build of the target (%d lines)'%len(latestImplicitInputs),
							lineterm='',
							n=0
							))
						if len(thediff)>10:
							thediff = thediff[:10]+['...']
						log.info('Up-to-date check: %s must be rebuilt because implicit inputs file has changed: "%s"\n\t%s\n', self.name, self._implicitInputsFile, 
							'\n\t'.join(thediff).replace('\r','\\r\r'))
						return False
					else:
						log.debug("Up-to-date check: implicit inputs file contents has not changed: %s", self._implicitInputsFile)
			else:
				log.debug("Up-to-date check: target has no implicitInputs data: %s", self)
			
			
			# NB: there shouldn't be any file system errors here since we've checked for the existence of deps 
			# already in _expand_deps; if this happens it's probably a build system bug
			stampmodtime = getmtime(self.stampfile)

			def isNewer(path):
				pathmodtime = getmtime(normLongPath(path))
				if pathmodtime <= stampmodtime: return False
				if pathmodtime-stampmodtime < 1: # such a small time gap seems dodgy
					log.warn('Up-to-date check: %s must be rebuilt because input file "%s" is newer than "%s" by just %0.1f seconds', self.name, path, self.stampfile, pathmodtime-stampmodtime)
				else:
					log.info('Up-to-date check: %s must be rebuilt because input file "%s" is newer than "%s" (by %0.1f seconds)', self.name, path, self.stampfile, pathmodtime-stampmodtime)
				return True

			for f in self.fdeps:
				if isdir(normLongPath(f)): 
					log.debug('Up-to-date check: walking dependency directory %s to check for newly modified files', f)
					for path, subdirs, files in os.walk(normLongPath(f)):
						for name in files:
							if isNewer(os.path.join(path, name)): return False
					log.debug('uptodate: done walking dependency directory %s', f)
				else:
					if isNewer(f): return False
		return True
		
	def run(self, context):
		"""
			Calls the wrapped run method
		"""
		implicitInputs = self.__getImplicitInputs(context)
		if implicitInputs or isDirPath(self.target.name):
			deleteFile(self._implicitInputsFile)
		
		self.target.run(context)
		
		# if target built successfully, record what the implicit inputs were to help with the next up to date 
		# check and ensure incremental build is correct
		if implicitInputs or isDirPath(self.target.name):
			log.debug('writing implicitInputsFile: %s', self._implicitInputsFile)
			mkdir(os.path.dirname(self._implicitInputsFile))
			iminpath = os.path.normpath(self._implicitInputsFile)
			if isWindows(): iminpath = u'\\\\?\\'+iminpath
			with openForWrite(iminpath, 'wb') as f:
				f.write(os.linesep.join(implicitInputs))
		
	def clean(self, context):
		"""
			Calls the wrapped clean method
		"""
		try:
			deleteFile(self._implicitInputsFile)
		except Exception:
			time.sleep(10.0)
			deleteFile(self._implicitInputsFile)
		self.target.clean(context)

	def internal_clean(self, context):
		"""
			Calls the BaseTarget clean, not the target-specific clean
		"""
		try:
			deleteFile(self._implicitInputsFile)
		except Exception:
			time.sleep(10.0)
			deleteFile(self._implicitInputsFile)
		BaseTarget.clean(self.target, context)


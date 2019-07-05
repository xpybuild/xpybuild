# xpyBuild - eXtensible Python-based Build System
#
# This class is responsible for working out what tasks need to run, and for 
# scheduling them
#
# Copyright (c) 2013 - 2017, 2019 Software AG, Darmstadt, Germany and/or its licensors
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
from utils.fileutils import deleteFile, mkdir, openForWrite, getmtime, exists, isfile, isdir, toLongPathSafe

import logging
log = logging.getLogger('scheduler.targetwrapper')

class TargetWrapper(object):
	"""
		Internal wrapper for a target which contains all the state needed by the 
		scheduler during builds. 
	"""
	
	__slots__ = 'target', 'path', 'name', 'isDirPath', 'lock', 'depcount', 'deps', '__rdeps', '__fdeps', '__isdirty', '__implicitInputs', '__implicitInputsFile', 'stampfile', 'effectivePriority'
	
	def __init__(self, target):
		"""
			Create a BuildTarget from a target. This target has an internal lock
			which is taken for some of the functions
		"""
		self.target = target
		self.path = target.path
		self.name = target.name
		self.isDirPath = isDirPath(target.name)

		self.lock = Lock()
		self.depcount = 0
		self.deps = None
		self.__rdeps = []
		self.__fdeps = []
		self.__isdirty = False
		
		self.__implicitInputs = None

		
		self.__implicitInputsFile = self.__getImplicitInputsFile()
		if self.isDirPath: 
			self.stampfile = self.__implicitInputsFile # might as well re-use this for dirs
		else:
			self.stampfile = self.target.path

		self.effectivePriority = target.getPriority() # may be mutated to an effective priority


	def __hash__ (self): return hash(self.target) # delegate
	
	def __str__(self): return '%s'%self.target # display string for the underlying target
	def __repr__(self): return 'TargetWrapper.%s'%str(self)
	
	def __getattr__(self, name):
		# note: getattr is very inefficient so don't use this for anything performance-critical

		# sometimes a TargetWrapper is passed to BuildException which calls .location on it
		if name == 'location': return self.target.location
				
		raise AttributeError('Unknown attribute %s' % name)
	
	def setEffectivePriority(self, pri):
		self.effectivePriority = pri
	
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

		# list os already sorted (in case of determinism problems with filesystem walk order)
		# take a copy here since it is used from other places
		x = list(self.resolveDependencies(context))
		
		# since this is meant to be a list of lines, normalize with a split->join
		# also make any non-linesep \r or \n chars explicit to avoid confusion when diffing
		x += [x.replace('\r','\\r').replace('\n','\\n') for x in os.linesep.join(self.target.getHashableImplicitInputs(context)).split(os.linesep)]
		
		self.__implicitInputs = x
		return x

	
	def resolveDependencies(self, context):
		"""
			Calls through to the wrapped target, which does the expansion/replacement
			of dependency strings here.
			
			Returns a SORTED list of dependencies as strings (paths). Either files or targets.
			
			Not not modify the returned list.
		"""
		if self.deps is not None: return self.deps

		# note that some of these may be PathSetGeneratedByTarget path sets where 
		# the real list of dependencies is not yet known, and the target that 
		# will generate them is specified instead
		deps = self.target._resolveUnderlyingDependencies(context)
		
		deps = context._expandAtomicDeps(deps)

		if self.path in deps: deps.remove(self.path)
		
		deps.sort()
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
			
			Returns the previous value of __isdirty, i.e. True if this was a no-op. 
		"""
		with self.lock:
			r = self.__isdirty
			self.__isdirty = True
			return r
			
	def rdep(self, target):
		"""
			Adds a reverse dependency to this target
			Holds the object lock
		"""
		with self.lock:
			self.__rdeps.append(target)
	def rdeps(self):
		"""
			Returns the list of reverse dependencies.
			Holds the object lock
		"""
		with self.lock:
			return self.__rdeps
	def filedep(self, path):
		"""
			Adds to the list of file dependencies. Not called for directories. 
			Holds the object lock
		"""
		with self.lock:
			self.__fdeps.append(path)
	def uptodate(self, context, ignoreDeps):
		"""
			Checks whether the target needs to be rebuilt.
			Returns true if the target is up to date and does not need a rebuild
			Holds the object lock
			
			Called during the main build phase, after the dependency resolution phase
		"""
		with self.lock:
			log.debug('Up-to-date check for %s', self.name)
			
			if self.__isdirty: 
				# no need to log at info, will already have been done when it was marked dirty
				log.debug('Up-to-date check: %s has been marked dirty', self.name)
				return False

			if not exists(self.path):
				log.debug('Up-to-date check: %s must be built because file does not exist: "%s"', self.name, self.path)
				self.__isdirty = True # make sure we don't log this again
				return False
			
			if ignoreDeps: return True
			
			if not isfile(self.stampfile): # this is really an existence check, but if we have a dir it's an error so ignore
				# for directory targets
				log.info('Up-to-date check: %s must be rebuilt because stamp file does not exist: "%s"', self.name, self.stampfile)
				return False
			
			# assume that by this point our explicit dependencies at least exist, so it's safe to call getHashableImplicitDependencies
			implicitInputs = self.__getImplicitInputs(context)
			if implicitInputs or self.isDirPath:
				# this is to cope with targets that have implicit inputs (e.g. globbed pathsets); might as well use the same mechanism for directories (which need a stamp file anyway)
				if not exists(self.__implicitInputsFile):
					log.info('Up-to-date check: %s must be rebuilt because implicit inputs/stamp file does not exist: "%s"', self.name, self.__implicitInputsFile)
					return False
				with open(toLongPathSafe(self.__implicitInputsFile), 'rb') as f:
					latestImplicitInputs = f.read().split(os.linesep)
					if latestImplicitInputs != implicitInputs:
						maxdifflines = int(os.getenv('XPYBUILD_IMPLICIT_INPUTS_MAX_DIFF_LINES', '30'))/2
						added = ['+ %s'%x for x in implicitInputs if x not in latestImplicitInputs]
						removed = ['- %s'%x for x in latestImplicitInputs if x not in implicitInputs]
						# the end is usually more informative than beginning
						if len(added) > maxdifflines: added = ['...']+added[len(added)-maxdifflines:] 
						if len(removed) > maxdifflines: removed = ['...']+removed[len(removed)-maxdifflines:]
						if not added and not removed: added = ['N/A']
						log.info('Up-to-date check: %s must be rebuilt because implicit inputs file has changed: "%s"\n\t%s\n', self.name, self.__implicitInputsFile, 
							'\n\t'.join(
								['previous build had %d lines, current build has %d lines'%(len(latestImplicitInputs), len(implicitInputs))]+removed+added
							).replace('\r','\\r\r'))
						return False
					else:
						log.debug("Up-to-date check: implicit inputs file contents has not changed: %s", self.__implicitInputsFile)
			else:
				log.debug("Up-to-date check: target has no implicitInputs data: %s", self)
			
			
			# NB: there shouldn't be any file system errors here since we've checked for the existence of deps 
			# already in _expand_deps; if this happens it's probably a build system bug
			stampmodtime = getmtime(self.stampfile)

			def isNewer(path):
				pathmodtime = getmtime(toLongPathSafe(path))
				if pathmodtime <= stampmodtime: return False
				if pathmodtime-stampmodtime < 1: # such a small time gap seems dodgy
					log.warn('Up-to-date check: %s must be rebuilt because input file "%s" is newer than "%s" by just %0.1f seconds', self.name, path, self.stampfile, pathmodtime-stampmodtime)
				else:
					log.info('Up-to-date check: %s must be rebuilt because input file "%s" is newer than "%s" (by %0.1f seconds)', self.name, path, self.stampfile, pathmodtime-stampmodtime)
				return True

			for f in self.__fdeps:
				if isNewer(f): return False
		return True
		
	def run(self, context):
		"""
			Calls the wrapped run method
		"""
		implicitInputs = self.__getImplicitInputs(context)
		if implicitInputs or self.isDirPath:
			deleteFile(self.__implicitInputsFile)
		
		self.target.run(context)
		
		# if target built successfully, record what the implicit inputs were to help with the next up to date 
		# check and ensure incremental build is correct
		if implicitInputs or self.isDirPath:
			log.debug('writing implicitInputsFile: %s', self.__implicitInputsFile)
			mkdir(os.path.dirname(self.__implicitInputsFile))
			with openForWrite(toLongPathSafe(self.__implicitInputsFile), 'wb') as f:
				f.write(os.linesep.join(implicitInputs))
		
	def clean(self, context):
		"""
			Calls the wrapped clean method
		"""
		try:
			deleteFile(self.__implicitInputsFile)
		except Exception:
			time.sleep(10.0)
			deleteFile(self.__implicitInputsFile)
		self.target.clean(context)

	def internal_clean(self, context):
		"""
			Calls the BaseTarget clean, not the target-specific clean
		"""
		try:
			deleteFile(self.__implicitInputsFile)
		except Exception:
			time.sleep(10.0)
			deleteFile(self.__implicitInputsFile)
		BaseTarget.clean(self.target, context)


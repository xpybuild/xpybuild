# xpyBuild - eXtensible Python-based Build System
#
# Copyright (c) 2013 - 2019 Software AG, Darmstadt, Germany and/or its licensors
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
# $Id: unpack.py 301527 2017-02-06 15:31:43Z matj $
#

import os, inspect, os.path
import time
import zipfile
import tarfile

from xpybuild.buildcommon import *
from xpybuild.pathsets import PathSet, BasePathSet
from xpybuild.basetarget import BaseTarget
from xpybuild.utils.fileutils import mkdir, deleteDir, normLongPath
from xpybuild.utils.antglob import antGlobMatch
from xpybuild.utils.flatten import flatten
from xpybuild.utils.buildfilelocation import BuildFileLocation
from xpybuild.utils.buildexceptions import BuildException

class Tarball(BaseTarget):
	""" Target that creates a .tar archive from a set of input files.
	"""

	def __init__(self, archive, inputs):
		"""
		archive: the archive to be created

		inputs: the files (usually pathsets) to be included in the archive.

		"""
		self.inputs = PathSet(inputs)
		BaseTarget.__init__(self, archive, self.inputs)

	def run(self, context):
		mkdir(os.path.dirname(self.path))
		with tarfile.open(normLongPath(self.path), 'w:gz') as output:
			for (f, o) in self.inputs.resolveWithDestinations(context):
				output.add(normLongPath(f).rstrip('/\\'), o)

	def getHashableImplicitInputs(self, context):
		r = super(Tarball, self).getHashableImplicitInputs(context)
		
		# include source representation of deps list, so that changes to the list get reflected
		# this way of doing property expansion on the repr is a convenient 
		# shortcut (we want to expand property values to detect changes in 
		# versions etc that should trigger a rebuild, but just not do any 
		# globbing/searches here)
		r.append('src: '+context.expandPropertyValues(('%s'%self.inputs)))
		
		return r

class Zip(BaseTarget):
	""" Target that creates a zip archive from a set of input files.
	"""

	def __init__(self, archive, inputs):
		"""
		archive: the archive to be created

		inputs: the files (usually pathsets) to be included in the archive.

		"""
		self.inputs = PathSet(inputs)
		BaseTarget.__init__(self, archive, self.inputs)

	def run(self, context):
		mkdir(os.path.dirname(self.path))
		alreadyDone = set()
		with zipfile.ZipFile(normLongPath(self.path), 'w') as output:
			for (f, o) in self.inputs.resolveWithDestinations(context):
				# if we don't check for duplicate entries we'll end up creating an invalid zip
				if o in alreadyDone:
					dupsrc = ['"%s"'%src for (src, dest) in self.inputs.resolveWithDestinations(context) if dest == o]
					raise BuildException('Duplicate zip entry "%s" from: %s'%(o, ', '.join(dupsrc)))
				alreadyDone.add(o)
				# can't compress directory entries! (it messes up Java)
				output.write(normLongPath(f).rstrip('/\\'), o, zipfile.ZIP_STORED if isDirPath(f) else zipfile.ZIP_DEFLATED) 

	def getHashableImplicitInputs(self, context):
		r = super(Zip, self).getHashableImplicitInputs(context)
		
		# include source representation of deps list, so that changes to the list get reflected
		# this way of doing property expansion on the repr is a convenient 
		# shortcut (we want to expand property values to detect changes in 
		# versions etc that should trigger a rebuild, but just not do any 
		# globbing/searches here)
		r.append('src: '+context.expandPropertyValues(('%s'%self.inputs)))
		
		return r


################################################################################
# For unpacking

def _getnames(file):
	if isinstance(file, zipfile.ZipFile):
		return file.namelist()
	elif isinstance(file, tarfile.TarFile):
		return file.getnames()
	else:
		assert False, "Should not happen, it's not a tarfile or a zipfile"

def _getinfo(file, name):
	if isinstance(file, zipfile.ZipFile):
		return file.getinfo(name)
	elif isinstance(file, tarfile.TarFile):
		return file.getmember(name)
	else:
		assert False, "Should not happen, it's not a tarfile or a zipfile"

def _setfilename(info, filename):
	if isinstance(info, zipfile.ZipInfo):
		info.filename = filename
		return info.filename
	elif isinstance(info, tarfile.TarInfo):
		info.name = filename
		return info.name
	else:
		assert False, "Should not happen, it's not a tarfile or a zipfile"

def _getfilename(info):
	if isinstance(info, zipfile.ZipInfo):
		return info.filename
	elif isinstance(info, tarfile.TarInfo):
		return info.name
	else:
		assert False, "Should not happen, it's not a tarfile or a zipfile"

class Unpack(BaseTarget):
	""" Target that creates a new directory containing the unpacked contents 
	of one or more archives (e.g. .zip files). 
	
	The parent directory will be created if it doesn't exist already. 
	"""
	
	def __init__(self, dest, archives): 
		"""
		@param dest: the output directory (ending with a "/"). Never 
		specify a dest directory that is also written to by another 
		target (e.g. do not specify a build 'output' directory here). 
			
		@param archives: the input archives to be unpacked, which may be any 
		combination of strings, PathSets, FilteredArchiveContents and lists of these. 
		If these PathSets include mapping information, this 
		will be used to define where (under the dest directory) each 
		file from within that archive is copied (but cannot be used to 
		change the archive-relative path of each item). 
		
		For advanced cases, FilteredArchiveContents can be used to provide 
		customized mapping and filtering of the archive contents, 
		including manipulation of the destinations encoded within the 
		archive itself. 
		
		"""
		if not dest.endswith('/'): raise BuildException('Unpack target destination must be a directory (ending with "/"), not: "%s"'%dest)
		
		# NB: we could also support copying in non-archived files into the directory future too
		
		# we should preserve the specified order of archives since it may 
		# affect what happens when they contain the same files and must 
		# overwrite each other
		
		archives = [a if (isinstance(a, BasePathSet) or isinstance(a, FilteredArchiveContents)) else PathSet(a) for a in flatten(archives)]
		
		BaseTarget.__init__(self, dest, [
			(a.getDependency() if isinstance(a, FilteredArchiveContents) else a)
			for a in archives])
		self.archives = archives
	
	def __openArchive(self, path):
		if path.lower().endswith('.zip') or path.lower().endswith('.jar') or path.lower().endswith('.war'):
			return zipfile.ZipFile(path, 'r')
		if path.lower().endswith('.tar.gz') or path.lower().endswith('.tar.bz2') or path.lower().endswith('.tar'):
			return tarfile.open(path, 'r')
		raise BuildException('Unsupported archive type: %s'%path)
	
	def run(self, context):
		self.log.info('Cleaning existing files from %s', self.path)
		deleteDir(self.path)
		
		iswindows = IS_WINDOWS
		
		for a in self.archives:
			a_is_filteredarchivecontents = isinstance(a, FilteredArchiveContents)
			if a_is_filteredarchivecontents:
				items = [(a.getResolvedPath(context), '')]
			else:
				assert isinstance(a, BasePathSet)
				filteredMembers = None
				items = a.resolveWithDestinations(context)
			for (srcAbs, destRel) in items:
				if destRel and not isDirPath(destRel): destRel = os.path.dirname(destRel) # strip off the zip filename
				if '..' in destRel: raise Exception('This target does not permit destination paths to contain ".." relative path expressions')
					
				try:
					filesize = os.path.getsize(srcAbs)
				except Exception:
					filesize = 0
				
				self.log.info("Unpacking %s (%0.1f MB) to %s", os.path.basename(srcAbs), filesize/1024.0/1024, self.name+destRel)
				starttime = time.time()
				with self. __openArchive(srcAbs) as f:
					mkdir(self.path+destRel)
					if a_is_filteredarchivecontents and a.hasIncludeExcludeFilters():
						fullList = _getnames(f)
						if not fullList:
							raise BuildException('No files were found in archive "%s"'%(srcAbs))
						filteredMembers = [x for x in fullList if a.isIncluded(context, x)]
						self.log.info("Unpacking %d of %d members in %s", len(filteredMembers), len(fullList), os.path.basename(srcAbs))
						if not filteredMembers:
							raise BuildException('No files matching the specified include/exclude filters were found in archive "%s": %s'%(srcAbs,  a))
						if len(filteredMembers)==len(fullList):
							raise BuildException('No files were excluded from the unpacking operation by the specified filters (check filters are correct): %s'%a)
					else:
						filteredMembers = _getnames(f)
					# NB: some archive types want a list of string members, others want TarInfo objects etc, so 
					# if we support other archive types in future might need to do a bit of work here
					path = normLongPath(self.path+destRel)
					for m in filteredMembers:						
						if not isDirPath(m):
							info = _getinfo(f, m)
							if a_is_filteredarchivecontents:
								_setfilename(info, a.mapDestPath(context, _getfilename(info)))
							if iswindows: _setfilename(info, _getfilename(info).replace('/', '\\'))
							f.extract(info, path=path)
						else:
							# we should create empty directories too
							if a_is_filteredarchivecontents:
								m = a.mapDestPath(context, m).rstrip('/')

							m = path.rstrip('/\\')+'/'+m
							if iswindows: m = m.replace('/', '\\')
							mkdir(m)
							
				
				self.log.info("Completed unpacking %s (%0.1f MB) in %0.1f seconds", os.path.basename(srcAbs), filesize/1024.0/1024, (time.time()-starttime))

	def getHashableImplicitInputs(self, context):
		# TODO: move this into BaseTarget
		r = super(Unpack, self).getHashableImplicitInputs(context)
		
		# include source representation of archives list, so that changes to the list get reflected
		# this way of doing property expansion on the repr is a convenient 
		# shortcut (we want to expand property values to detect changes in 
		# versions etc that should trigger a rebuild, but just not do any 
		# globbing/searches here)
		r.append('archives: '+context.expandPropertyValues(str(self.archives)))
		
		return r


class FilteredArchiveContents(object): 
	"""Object representing an archive to be passed to the Unpack target, with 
	support for filtering which files are included/excluded, and per-item 
	destination mapping. 
	
	"""
	
	# do NOT use pathset baseclass, because we need the target to handle it in 
	# a custom way for both per-archived-file mapping and in-archive filtering, 
	# which would be wrecked by the normalization stuff that pathset does; 
	# also the model is a bit different for archive contents, so simplest 
	# just to keep it separate
	
	def __init__(self, archivePath, includes=None, excludes=None, destMapper=None):
		"""
		@param archivePath: The archive to unpack; either a string or a singleton PathSet

		@param destMapper: A functor that takes a (context, destPath) where destPath 
		is an archive-relative path (guaranteed to contain / not \\), and 
		returns the desired destination relative path string. 
		The functor should have a deterministic and 
		user-friendly __str__ implementation. 

		@param includes: a list of include patterns (if provided excludes all non-matching files)

		@param excludes: a list of exclude patterns (processed after includes)
		"""
		self.__path = PathSet(archivePath)
		self.__destMapper = destMapper
		self.__includes = flatten(includes)
		self.__excludes = flatten(excludes)
		self.__location = BuildFileLocation()
		self.__isResolved = False
	
	def getDependency(self):
		""" Return the dependency representing this archive (unexpanded and unresolved string, or PathSet). 
		"""
		return self.__path

	def getResolvedPath(self, context):
		""" Return the fully resolved archive path. 
		"""
		result = self.__path.resolve(context)
		if len(result) != 1: raise Exception('Invalid PathSet specified for FilteredArchiveContents, must resolve to exactly one archive: %s'%self.__path)
		return result[0]
	
	def isIncluded(self, context, path):
		""" Decides whether the specified path within the archive should be 
		unpacked, based on the include/exclude filters
		
		@param path: a relative path within the archive
		"""
		if not self.__excludes and not self.__includes: return True
		if not self.__isResolved:
			self.__includes = flatten([context.expandPropertyValues(x, expandList=True) for x in self.__includes])
			self.__excludes = flatten([context.expandPropertyValues(x, expandList=True) for x in self.__excludes])
			self.__isResolved = True
		
		assert '\\' not in path
		try:
			path = path.lstrip('/')
				
			# first check if it matches an exclude
			if next( (True for e in self.__excludes if antGlobMatch(e, path)), False): return False
				
			if not self.__includes: # include everything
				return True
			else:
				m = next( (i for i in self.__includes if antGlobMatch(i, path)), None)
				if m: 
					return True
				else:
					return False
					
		except Exception as e:
			raise BuildException('FilteredArchiveContents error for %s'%(self), causedBy=True, location=self.__location)

	def hasIncludeExcludeFilters(self):
		return self.__includes or self.__excludes
	
	def mapDestPath(self, context, path):
		if not self.__destMapper: return path
		x = self.__destMapper(context, path.replace('\\','/'))
		if isDirPath(path) and not isDirPath(x): x += '/'
		return x
	
	def __repr__(self): 
		""" Returns a string including this class name, the archive path, the destination prefix 
		and any includes/excludes.
		"""
		return ('FilteredArchiveContents(%s, includes=%s, excludes=%s, destmapper=%s)'%(
			self.__path, self.__includes, self.__excludes, 'None' if not self.__destMapper else self.__destMapper.__name__)).replace('\'','"')

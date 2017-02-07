# xpyBuild - eXtensible Python-based Build System
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
# $Id: copy.py 301527 2017-02-06 15:31:43Z matj $
#

import os, inspect, os.path, re, shutil

from buildcommon import *
from pathsets import PathSet
from basetarget import BaseTarget
from utils.fileutils import mkdir, deleteDir, openForWrite, normLongPath
from utils.flatten import flatten
from utils.buildfilelocation import BuildFileLocation
from buildexceptions import BuildException

class Copy(BaseTarget):
	""" A target that copies input file(s) to an output file or directory. 
	
	The parent directory will be created if it doesn't exist already. 
	"""
	
	def __init__(self, dest, src, mode=None, implicitDependencies=None):
		"""
		dest - the output directory (ending with a "/") or file. Never 
			specify a dest directory that is also written to by another 
			target (e.g. do not specify an output directory here). If you need 
			to write multiple files to a directory, use separate Copy 
			targets for each, with file (rather than directory) target dest 
			names. 
			
		src - the input, which may be any combination of strings, PathSets and 
			lists of these. If these PathSets include mapping information, this 
			will be used to define where (under the dest directory) each 
			file is copied. 
			
			Note that only src files will be copied, any directory in the 
			src list will be created but its contents will not be copied 
			across - the only way to copy a directory is to use a FindPaths
			(or FindPaths(DirGeneratedByTarget('...'))) 
			for the src, which has the ability to find its contents on disk 
			(this is necessary to prevent complex race conditions and 
			build errors arising from implicit directory walking during 
			the execution phase - if all dir walking happens during 
			dependency resolution then such errors can be easily detected 
			before they cause a problem). 
		
		mode -- unix permissions to set with chmod on the destination files. 
			If not specified, mode is simply copied from source file. 
		
		implicitDependencies -- provides a way to add additional implicit 
			dependencies that will not be part of src but may affect the 
			copy process (e.g. filtering in); this is intended for 
			use by subclasses, do not set this explicitly. 
		"""
		if mode: raise Exception(dest)
		src = PathSet(src)
		BaseTarget.__init__(self, dest, [src, implicitDependencies])
		self.src = src
		self.mode = mode
			
	def run(self, context):
		self.log.info("Copying %s to %s", self.src, self.path)

		src = self.src.resolveWithDestinations(context) #  a map of srcAbsolute: destRelative

		# implicitly ensure parent of target exists, to keep things simple
		
		copied = 0
		if not isDirPath(self.name):
			# it's a simple file operation.
			if len(src) != 1:
				raise BuildException('Copy destination must be a directory (ending with "/") when multiple sources are specified (not: %s)' % src)
			src, mappedDest = src[0]
			if isDirPath(src):
				raise BuildException('Copy source must be files (or PathSets) not directories: %s'%src)
			mkdir(os.path.dirname(self.path))
			self._copyFile(context, src, self.path) # we kindof have to ignore mappedDest here, since the target path already fully defines it
			if self.mode:
				os.chmod(self.path, self.mode)
			copied += 1
		else:
			lastDirCreated = None
			
			for (srcAbs, destRel) in src:
				# there should not be any directories here only files from pathsets
				if '..' in destRel:
					# to avoid people abusing this to copy files outside the dest directory!
					raise Exception('Cannot use ".." relative path expressions in a Copy target')
				if isDirPath(srcAbs): # allows creating of empty directories. 
					mkdir(self.path+destRel)
				else:
					dest = os.path.normpath(self.path+destRel)
					#self.log.debug('Processing %s -> %s i.e. %s', srcAbs, destRel, dest)
					
					if not lastDirCreated or lastDirCreated!=os.path.dirname(dest):
						lastDirCreated = os.path.dirname(dest)
						self.log.debug('Creating intermediate dir %s', lastDirCreated)
						mkdir(lastDirCreated)
					
					try:
						self._copyFile(context, srcAbs, dest)
						if self.mode:
							os.chmod(dest, self.mode)
					except Exception, e:
						raise BuildException('Error copying from "%s" to "%s"'%(srcAbs, dest), causedBy=True)
						
					copied += 1
				
		self.log.info('Copied %d file(s) to %s', copied, self.path)
	
	def _copyFile(self, context, src, dest):
		src = normLongPath(src)
		dest = normLongPath(dest)
		with open(src, 'rb') as inp:
			with openForWrite(dest, 'wb') as out:
				shutil.copyfileobj(inp, out)
		shutil.copymode(src, dest)
		assert os.path.exists(dest)
	
	def getHashableImplicitInputs(self, context):
		# TODO: move this into BaseTarget
		r = super(Copy, self).getHashableImplicitInputs(context)
		
		# include source representation of deps list, so that changes to the list get reflected
		# this way of doing property expansion on the repr is a convenient 
		# shortcut (we want to expand property values to detect changes in 
		# versions etc that should trigger a rebuild, but just not do any 
		# globbing/searches here)
		r.append('src: '+context.expandPropertyValues('%s'%self.src))
		
		if self.mode: r.append('mode: %s'%self.mode)
		
		return r

class FilteredCopy(Copy):
	""" A target that copies input text file(s) to an output file or directory, 
		filtering each line through the specified line mappers. 
	
	The parent directory will be created if it doesn't exist already. 

	"""
	
	def __init__(self, dest, src, *mappers):
		"""
		dest - the output directory (ending with a "/") or file. Never 
			specify a dest directory that is also written to by another 
			target (e.g. do not specify an output directory here). If you need 
			to write multiple files to the output directory, use separate Copy 
			targets for each. 
			
		src - the input, which may be any combination of strings, PathSets and 
			lists of these. 
		
		mappers -- a list of mapper objects that will be used to transform 
			the file, line by line. To avoid build files that accumulate unused 
			cruft or are hard to understand, it is an error to include a mapper 
			in this list that is not used, i.e. that does not in any way 
			change the output. 
			
			For simple @TOKEN@ replacement see createReplaceDictLineMappers. 
			In addition to per-line changes, it is also possible to specify 
			mappers that add header/footer content to the file. 
			
			Note that files are read and written in binary mode, so mappers 
			will be dealing directly with platform-specific \n and \r 
			characters; python's os.linesep should be used where a 
			platform-neutral newline is required. 
		
		"""
		assert mappers
		self.mappers = [m.getInstance() for m in flatten(mappers)]
		super(FilteredCopy, self).__init__(dest, src, implicitDependencies=[m.getDependencies() for m in self.mappers])
	
	def run(self, context):
		self.__unusedMappers = set(self.mappers)
		super(FilteredCopy, self).run(context)
		
		if self.__unusedMappers:
			# a useful sanity check, to ensure we're replacing what we think we're replacing, and also that we don't have unused clutter in the build files
			raise BuildException('Some of the specified mappers did not get used at all during the copy (to avoid confusion, mappers that do not change the output in any way are not permitted): %s'%(', '.join( [m.getDescription(context) for m in self.__unusedMappers] )))
			
	def getHashableImplicitInputs(self, context):
		""" Include the mapper descriptions in the implicit dependencies. """
		r = super(FilteredCopy, self).getHashableImplicitInputs(context)
		for m in self.mappers: r.append(m.getDescription(context)) # ensures that changes to properties force a rebuild when necessary
		return r
		
	def _copyFile(self, context, src, dest):
		dest = normLongPath(dest)
		src = normLongPath(src)
		with open(src, 'rb') as s:
			with openForWrite(dest, 'wb') as d:
				for m in self.mappers:
					x = m.getHeader(context)
					if x: 
						self.__unusedMappers.discard(m)
						d.write(x)
				
				for l in s:
					for m in self.mappers:
						prev = l
						l = m.mapLine(context, l)
						if prev != l:
							self.__unusedMappers.discard(m)
						if None == l:
							break
					if None != l:
						d.write(l)

				for m in self.mappers:
					x = m.getFooter(context)
					if x: 
						self.__unusedMappers.discard(m)
						d.write(x)
		shutil.copymode(src, dest)
		assert os.path.exists(dest)

class FileContentsMapper(object):
	""" A base class for mappers that take part in text file transformation for use with FilteredCopy
	
	Note that files are read and written in binary mode, so mappers 
	will be dealing directly with platform-specific \n and \r 
	characters; python's os.linesep should be used where a 
	platform-netural new line character is required. 

	 """
	def getInstance(self): 
		""" Called when a target begins to use a (potentially shared) line mapper. 
		Returns the thread-safe (or stateless) FileContentsMapper instance that will be used; 
		since most instancea are inherently stateless, by default just returns self. 
		"""
		return self
	def mapLine(self, context, line): 
		""" Called for every line in the file, returning the original line, a changed line, or None if the line should be deleted. 
		"""
		raise Exception('Not implemented yet')
	def getHeader(self, context): 
		"""
		Called at the start of every file. By default returns None but can return 
		a string that will be written to the target file before anything else. 
		"""
		return None
	def getFooter(self, context): 
		"""
		Called at the end of every file. By default returns None but can return 
		a string that will be written to the target file after everything else. 
		"""
		return None
	def getDescription(self, context): 
		""" Returns a string description of the transformation, to be used for up-to-date rebuild checking"""
		raise Exception('Not implemented yet')
	def getDependencies(self): 
		""" Advanced option for specifying paths that are required to be read by this line mapper, 
		which therefore should be dependencies of the target that uses it. Returns a list of unresolved paths. 
		"""
		return []

class OmitLines(FileContentsMapper):
	""" Omits lines from the input which contain the specified regular 
	expression. Use re.escape() on the input if a simple substring match is 
	required. 
	"""
	def __init__(self, match):	self.match = match
	def mapLine(self, context, line): return None if re.search(self.match, line) else line
	def getDescription(self, context): return 'OmitLines("%s")' % self.match

class StringReplaceLineMapper(FileContentsMapper):
	""" Performs a simple string replacement for a single key/value.
	Any ${...} xpybuild properties in the old and new strings will be expanded. 

	Usually will be created from a dictionary of tokens and replacements by L{createReplaceDictLineMappers}
	"""
	def __init__(self, old, new): self.old, self.new = old, new
	def mapLine(self, context, line): return line.replace(context.expandPropertyValues(self.old), context.expandPropertyValues(self.new))
	def getDescription(self, context): return 'StringReplaceLineMapper("%s" -> "%s")'%(context.expandPropertyValues(self.old), context.expandPropertyValues(self.new))

class RegexLineMapper(FileContentsMapper):
	""" Performs a regex substitution ; any ${...} xpybuild properties in 
	the replacement string will be expanded, but not in the regex string. 
	
	Note that files are written in binary mode, so rather than hardcoding 
	"\n", python's os.linesep should be used where a platform-neutral newline 
	is required. 

	"""
	def __init__(self, regex, repl): self.regex, self.repl = regex, repl
	def __getReplacement(self, context): return context.expandPropertyValues(self.repl.replace('\\', '!xpybuildslash!')).replace('\\', '\\\\').replace('!xpybuildslash!', '\\')
	def mapLine(self, context, line): return re.sub(self.regex, self.__getReplacement(context), line)
	def getDescription(self, context): return 'RegexLineMapper("%s" -> "%s")'%(self.regex, self.__getReplacement(context))

class InsertFileContentsLineMapper(FileContentsMapper):
	""" Replace instances of the specified token with the entire contents of the specified file
	
	filepath must be an absolute path, not a build dir relative path. 
	"""
	def __init__(self, replacementToken, filepath): 
		self.replacementToken, self.filepath = replacementToken, filepath
		self.baseDir = BuildFileLocation().buildDir
	def mapLine(self, context, line): 
		if self.replacementToken in line:
			with open(context.getFullPath(self.filepath, defaultDir=self.baseDir) , 'r') as f:
				contents = f.read()
			line = line.replace(self.replacementToken, contents)
		return line
	def getDescription(self, context): return 'InsertFileContentsLineMapper("%s" -> contents of "%s")'%(self.replacementToken, self.filepath)
	def getDependencies(self): return [self.filepath]

def createReplaceDictLineMappers(replaceDict, replaceMarker='@'):
	""" Create a list of line mappers based on the contents of the specified replaceDict, where 
	values containing ${...} properties will be expanded out. 

	replaceDict -- The dictionary of keys and values

	replaceMarker -- the delimiter for keys (default=@), e.g. @KEY@ will be replaced with VALUE
	"""
	return [StringReplaceLineMapper(replaceMarker+k+replaceMarker, replaceDict[k]) for k in replaceDict]

class AddFileHeader(FileContentsMapper):
	""" Add the specified string as a header at the 
	start of the file. Note that if a trailing newline is required before 
	the rest of the file's contents it should be included as part of the header. 

	Property substitution will be performed on the specified string. 

	Note that files are written in binary mode, so rather than hardcoding 
	"\n", python's os.linesep should be used where a platform-neutral newline 
	is required. 

	"""
	def __init__(self, string): self.s = string
	def mapLine(self, context, line): return line
	def getHeader(self, context): return context.expandPropertyValues(self.s)
	def getDescription(self, context): return 'AddFileHeader("%s")'%(self.s.replace('\r','\\r').replace('\n','\\n'))

class AddFileFooter(FileContentsMapper):
	""" Add the specified string as a footer at the 
	end of the file. Note that if a trailing newline is required at the end 
	of the file it should be included as part of the footer. 

	Property substitution will be performed on the specified string. 

	Note that files are written in binary mode, so rather than hardcoding 
	"\n", python's os.linesep should be used where a platform-neutral newline 
	is required. 

	"""
	def __init__(self, string): self.s = string
	def mapLine(self, context, line): return line
	def getFooter(self, context): return context.expandPropertyValues(self.s)
	def getDescription(self, context): return 'AddFileFooter("%s")'%(self.s.replace('\r','\\r').replace('\n','\\n'))

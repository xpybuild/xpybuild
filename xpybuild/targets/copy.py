# xpyBuild - eXtensible Python-based Build System
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
# $Id: copy.py 301527 2017-02-06 15:31:43Z matj $
#


"""
Contains the :obj:`xpybuild.targets.copy.Copy` target for binary file and directory copies, and 
the :obj:`xpybuild.targets.copy.FilteredCopy` target for copying text file(s) while filtering their contents 
through a set of mappers. 

`FilteredCopy` uses one or more instances of :obj:`xpybuild.targets.copy.FileContentsMapper` to map from 
source to destination file contents. Several pre-defined mappers are provided:

.. autosummary::
	StringReplaceLineMapper
	createReplaceDictLineMappers
	RegexLineMapper
	OmitLines
	InsertFileContentsLineMapper
	AddFileHeader
	AddFileFooter

"""

import os, inspect, os.path, re, shutil
from stat import S_ISLNK

from xpybuild.buildcommon import *
from xpybuild.propertysupport import defineOption, ExtensionBasedFileEncodingDecider
from xpybuild.pathsets import PathSet
from xpybuild.basetarget import BaseTarget
from xpybuild.utils.fileutils import mkdir, deleteDir, openForWrite, normLongPath
from xpybuild.utils.flatten import flatten
from xpybuild.utils.buildfilelocation import BuildFileLocation
from xpybuild.utils.buildexceptions import BuildException

class Copy(BaseTarget):
	""" Target that copies input file(s) to an output file or directory. 
	
	The parent directory will be created if it doesn't exist already. 

	The 'Copy.symlinks' option can be set to True if symbolic links 
	in the source should result in the creation of symbolic links 
	in the destination. 
	"""
	def __init__(self, dest, src, implicitDependencies=None):
		"""
		@param dest: the output directory (ending with a "/") or file. Never 
		specify a dest directory that is also written to by another 
		target (e.g. do not specify an output directory here). If you need 
		to write multiple files to a directory, use separate Copy 
		targets for each, with file (rather than directory) target dest 
		names. 
			
		@param src: the input, which may be any combination of strings, PathSets and 
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
		
		To create new empty directories that are not present in the source (mkdir), 
		you can use this simple trick which utilizes the fact that the current 
		directory ``.`` definitely exists. It doesn't copy anything from inside 
		(just copies only its 'existence') and uses a SingletonDestRenameMapper PathSet 
		to provide the destination::
		
			SingletonDestRenameMapper('my-new-dest-directory/', './'),
		
		@param implicitDependencies: provides a way to add additional implicit 
		dependencies that will not be part of src but may affect the 
		copy process (e.g. filtering in); this is intended for 
		use by subclasses, do not set this explicitly. 
		"""
		src = PathSet(src)
		BaseTarget.__init__(self, dest, [src, implicitDependencies])
		self.src = src
		self.mode = None # not yet supported, but may be if it turns out to be useful
		self.addHashableImplicitInputOption('Copy.symlinks')
			
	def run(self, context):
		self.log.info("Copying %s to %s", self.src, self.path)

		src = self.src.resolveWithDestinations(context) #  a map of srcAbsolute: destRelative

		symlinks = self.options['Copy.symlinks']
		if isinstance(symlinks, str): symlinks = symlinks.lower()=='true'
		assert symlinks in [True,False], repr(symlinks)

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
				srcAbs = normLongPath(srcAbs)
				dest = normLongPath(self.path+destRel)
				# there should not be any directories here only files from pathsets
				if '..' in destRel:
					# to avoid people abusing this to copy files outside the dest directory!
					raise Exception('This target does not permit destination paths to contain ".." relative path expressions')
				issymlink = symlinks and os.path.islink(srcAbs.rstrip(os.sep))

				if isDirPath(srcAbs) and not issymlink: # allows creating of empty directories. 
					mkdir(dest)
				else:
					#self.log.debug('Processing %s -> %s i.e. %s', srcAbs, destRel, dest)

					if issymlink: # this may be a directory path, and dirname will fail unless we strip off the /
						dest = dest.rstrip(os.sep)
					
					if not lastDirCreated or lastDirCreated!=os.path.dirname(dest):
						lastDirCreated = os.path.dirname(dest)
						self.log.debug('Creating intermediate dir %s', lastDirCreated)
						mkdir(lastDirCreated)
					
					try:
						if issymlink:
							os.symlink(os.readlink(srcAbs.rstrip(os.sep)), dest)	
						else:
							self._copyFile(context, srcAbs, dest)
							if self.mode:
								os.chmod(dest, self.mode)
					except Exception as e:
						raise BuildException('Error copying from "%s" to "%s"'%(srcAbs, dest), causedBy=True)
						
					copied += 1
				
		self.log.info('Copied %d file(s) to %s', copied, self.path)
	
	def _copyFile(self, context, src, dest):
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

defineOption('Copy.symlinks', False)
""" If True, symbolic links in the source are represented as symbolic links 
(either absolute or relative) in the destination. If False (the default), symbolic links 
are handled by copying the contents of the linked files. 
"""

class FilteredCopy(Copy):
	"""
	Target that copies one or more input text file(s) to an output file or directory, 
	filtering each line through the specified line mappers. 
	
	The parent directory will be created if it doesn't exist already. 
	
	Any source files determines to be binary/non-text by 
	`ExtensionBasedFileEncodingDecider.BINARY` are copied without any mappers 
	being invoked. 
	"""
	
	def __init__(self, dest, src, *mappers, **kwargs):
		"""
		@param dest: the output directory (ending with a ``/``) or file. Never 
			specify a dest directory that is also written to by another 
			target (e.g. do not specify an output directory here). If you need 
			to write multiple files to the output directory, use separate Copy 
			targets for each. 
		
		@param src: the input, which may be any combination of strings, PathSets and 
			lists of these. 
		
		@param mappers: a list of objects subclassing L{FileContentsMapper} 
			that will be used to transform 
			the file, line by line. Can be empty in which case this behaves the same 
			as a normal Copy target. Any items in this list with the value None 
			are ignored. 
			
			For simple @TOKEN@ replacement see createReplaceDictLineMappers. 
			In addition to per-line changes, it is also possible to specify 
			mappers that add header/footer content to the file. 
				
			Note that files are read and written in binary mode, so mappers 
			will be dealing directly with platform-specific ``\\n`` and ``\\r`` 
			characters; python's os.linesep should be used where a 
			platform-neutral newline is required. 
		
		@param allowUnusedMappers:
			To avoid build files that accumulate unused 
			cruft or are hard to understand, by default it is an error to include a 
			mapper in this list that is not used, i.e. that does not in any way 
			change the output for any file. We recommend using conditionalization 
			to avoid passing in such mappers e.g. ::

				FilteredCopy(target, src, [StringReplaceLineMapper(os.linesep,'\\n') if IS_WINDOWS else None]). 
			
			If this is not practical, set ``allowUnusedMappers=True`` to prevent this 
			check. 
		
		"""
		self.mappers = [m.getInstance() for m in flatten(mappers)]
		self.allowUnusedMappers = kwargs.pop('allowUnusedMappers', False)
		assert not kwargs, 'unknown keyword arg(s): %s'%kwargs
		super(FilteredCopy, self).__init__(dest, src, implicitDependencies=[m.getDependencies() for m in self.mappers])
		self.addHashableImplicitInputOption('common.fileEncodingDecider')
	
	def run(self, context):
		self.__unusedMappers = set(self.mappers)
		super(FilteredCopy, self).run(context)
		
		if self.__unusedMappers and not self.allowUnusedMappers:
			# a useful sanity check, to ensure we're replacing what we think we're replacing, and also that we don't have unused clutter in the build files
			raise BuildException('Some of the specified mappers did not get used at all during the copy (to avoid confusion, mappers that do not change the output in any way are not permitted): %s'%(', '.join( [m.getDescription(context) for m in self.__unusedMappers] )))
			
	def getHashableImplicitInputs(self, context):
		""" Include the mapper descriptions in the implicit dependencies. """
		r = super(FilteredCopy, self).getHashableImplicitInputs(context)
		for m in self.mappers: 
			m.prepare(context)
			r.append(m.getDescription(context)) # ensures that changes to properties force a rebuild when necessary
		return r
		
	def _copyFile(self, context, src, dest):
		if self.getOption('common.fileEncodingDecider')(context, src) == ExtensionBasedFileEncodingDecider.BINARY:
			return super()._copyFile(context, src, dest)
	
		mappers = [m for m in self.mappers if m.startFile(context, src, dest) is not False]
		
		try:
			with self.openFile(context, src, 'r', newline='\n') as s:
				# newline: for compatibility with existing builds, we don't expand \n to os.linesep (i.e. don't use Python universal newlines)
				with self.openFile(context, dest, 'w', newline='\n') as d:
					for m in mappers:
						x = m.getHeader(context)
						if x: 
							self.__unusedMappers.discard(m)
							d.write(x)
					
					for l in s:
						for m in mappers:
							prev = l
							l = m.mapLine(context, l)
							if prev != l:
								self.__unusedMappers.discard(m)
							if None == l:
								break
						if None != l:
							d.write(l)

					for m in mappers:
						x = m.getFooter(context)
						if x: 
							self.__unusedMappers.discard(m)
							d.write(x)
		except Exception as ex:
			exceptionsuffix = ''
			if isinstance(ex, UnicodeDecodeError):
				exceptionsuffix = ' due to encoding problem; consider setting the "common.fileEncodingDecider" option'
			raise BuildException(f'Failed to perform filtered copy of {src}{exceptionsuffix}',causedBy=True)
		shutil.copymode(src, dest)
		assert os.path.exists(dest)

class FileContentsMapper(object):
	""" A base class for mappers that take part in text file transformation for use with FilteredCopy
	
	Note that files are read and written in binary mode, so mappers 
	will be dealing directly with platform-specific \\n and \\r 
	characters; python's os.linesep should be used where a 
	platform-netural new line character is required. 

	"""
	
	def getInstance(self): 
		""" Called when a target begins to use a (potentially shared) line mapper. 
		Returns the thread-safe (or stateless) FileContentsMapper instance that will be used; 
		since most instances are inherently stateless, by default just returns self. 
		
		If you need to keep any state that changes after the L{prepare} method 
		is called (for example based on tracking the current filename or 
		previously encountered lines), you need to override this and return a new instance 
		either by calling your constructor or use Python's copy.deepcopy() method. 
		"""
		return self
	def prepare(self, context, **kwargs):
		""" Called once the build process has started and before any other method on this mapper 
		(other than getInstance) to allow the mapper to initialize its internal 
		variables using the build context, for example by expanding build properties. 
		"""
		pass
	def startFile(self, context, src, dest):
		""" Called when the mapper starts to process a new file. 
		
		Can be used to prevent the mapper handling certain files. 
		For stateful mappers (with an implementation of L(getInstance), this 
		can be used to enable file-specific behaviour during mapping. 
		
		@param context: The context. 
		@param src: The absolute normalized long-path-safe source file path. 
		@param dest: The absolute normalized long-path-safe destination file path. 
		@return: True if this file can be handled by this mapper, or False if 
		it should be ignored for this file. 
		"""
		return True
	def mapLine(self, context, line): 
		""" Called for every line in the file, returning the original line, a changed line, or None if the line should be deleted. 
		
		@param line: The input line as a byte string.
		@return: The line to write to output as a byte string, or None if it should be omitted. 
		"""
		raise Exception('Not implemented yet')
	def getHeader(self, context): 
		"""
		Called at the start of every file. By default returns None but can return 
		a string that will be written to the target file before anything else. 
		Use os.linesep for new lines. 
		"""
		return None
	def getFooter(self, context): 
		"""
		Called at the end of every file. By default returns None but can return 
		a string that will be written to the target file after everything else. 
		Use os.linesep for new lines. 
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
	
	@param disablePropertyExpansion: set to True to disable expansion of ${...} properties in the 
	old and new strings.
	"""
	def __init__(self, old, new, disablePropertyExpansion=False): self.old, self.new, self.disablePropertyExpansion = old, new, disablePropertyExpansion
	def prepare(self, context):
		if not self.disablePropertyExpansion: 
			self.old, self.new = context.expandPropertyValues(self.old), context.expandPropertyValues(self.new)
	def mapLine(self, context, line): return line.replace(self.old, self.new)
	def getDescription(self, context): return 'StringReplaceLineMapper("%s" -> "%s")'%(self.old, self.new)

class RegexLineMapper(FileContentsMapper):
	""" Performs a regex substitution ; any ${...} xpybuild properties in 
	the replacement string will be expanded, but not in the regex string. 
	
	Note that files are written in binary mode, so rather than hardcoding 
	the newline character "\\n", python's os.linesep should be used where a platform-neutral newline 
	is required. 

	"""
	def __init__(self, regex, repl, disablePropertyExpansion=False): 
		self.regex, self.repl, self.disablePropertyExpansion = regex, repl, disablePropertyExpansion
	def prepare(self, context):
		if not self.disablePropertyExpansion: 
			self.repl = context.expandPropertyValues(self.repl.replace('\\', '!xpybuildslash!')).replace('\\', '\\\\').replace('!xpybuildslash!', '\\')
	def mapLine(self, context, line): return re.sub(self.regex, self.repl, line)
	def getDescription(self, context): return 'RegexLineMapper("%s" -> "%s")'%(self.regex, self.repl)

class InsertFileContentsLineMapper(FileContentsMapper):
	""" Replace instances of the specified token with the entire contents of the specified file.
	
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
	"""
	Create a list of line mappers based on the contents of the specified replaceDict, where 
	values containing ${...} properties will be expanded out. 

	@param replaceDict: The dictionary of keys and values

	@param replaceMarker: the delimiter for keys (default=@), e.g. @KEY@ will be replaced with VALUE
	"""
	return [StringReplaceLineMapper(replaceMarker+k+replaceMarker, replaceDict[k]) for k in replaceDict]

class AddFileHeader(FileContentsMapper):
	"""
	Add the specified string as a header at the 
	start of the file. Note that if a trailing newline is required before 
	the rest of the file's contents it should be included as part of the header. 

	Property substitution will be performed on the specified string. 

	Note that files are written in binary mode, so rather than hardcoding 
	the newline character "\\n", python's os.linesep should be used where a platform-neutral newline 
	is required. 

	@param disablePropertyExpansion: set to True to disable expansion of ${...} properties in the 
	old and new strings.
	"""
	def __init__(self, string, disablePropertyExpansion=False): self.s, self.disablePropertyExpansion = string, disablePropertyExpansion
	def mapLine(self, context, line): return line
	def getHeader(self, context): return self.s if self.disablePropertyExpansion else context.expandPropertyValues(self.s)
	def getDescription(self, context): return 'AddFileHeader("%s")'%(self.getHeader(context).replace('\r','\\r').replace('\n','\\n'))

class AddFileFooter(FileContentsMapper):
	"""
	Add the specified string as a footer at the 
	end of the file. Note that if a trailing newline is required at the end 
	of the file it should be included as part of the footer. 
	
	Property substitution will be performed on the specified string. 
	
	Note that files are written in binary mode, so rather than hardcoding 
	the newline character "\\n", python's os.linesep should be used where a platform-neutral newline 
	is required. 
	
	@param disablePropertyExpansion: set to True to disable expansion of ${...} properties in the 
	old and new strings.
	"""
	def __init__(self, string, disablePropertyExpansion=False): self.s, self.disablePropertyExpansion = string, disablePropertyExpansion
	def mapLine(self, context, line): return line
	def getFooter(self, context): return self.s if self.disablePropertyExpansion else context.expandPropertyValues(self.s)
	def getDescription(self, context): return 'AddFileFooter("%s")'%(self.getFooter(context).replace('\r','\\r').replace('\n','\\n'))

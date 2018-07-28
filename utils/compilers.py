# xpyBuild - eXtensible Python-based Build System
#
# Copyright (c) 2014 - 2017 Software AG, Darmstadt, Germany and/or its licensors
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
# $Id: compilers.py 301527 2017-02-06 15:31:43Z matj $
#

import os, re, logging, time, traceback

from buildcommon import *
from buildexceptions import BuildException
from utils.process import call
from utils.outputhandler import ProcessOutputHandler
from propertysupport import defineOption

class Process(object):
	"""
	Parent type for compiler/tool chain process classes,
	contain helper method for calling the compiler process
	"""
	def __init__(self, environs=None):
		self.environs = environs or {}
	
	def getExpandedEnvirons(self, context, environs=None):
		"""
		Return the environment variables to be used for this process, 
		either passed explicitly into this method, or passed into 
		the constructor, or else empty. 
		
		Any ${...} substitution vars are expanded automatically.
		"""
		environs = environs or self.environs or {}
		environs = environs.copy()
		for k in environs:
			environs[k] = context.expandPropertyValues(environs[k])
		return environs
	
	def call(self, context, args, outputHandler, options, cwd=None, environs=None):
		try:
			args = flatten([context.expandPropertyValues(x, expandList=True) for x in args])
			
			try:
				outputHandlerInstance=outputHandler(os.path.basename(args[0]), options=options)
			except Exception, e:
				# backwards compatibility for output handlers that don't pass kwargs down
				outputHandlerInstance = outputHandler(os.path.basename(args[0]))
			
			call(args, outputHandler=outputHandlerInstance, cwd=cwd, env=self.getExpandedEnvirons(context, environs), timeout=options['process.timeout'])
		except BuildException as e:
			# causedBy is not useful here
			raise BuildException("%s process failed" % (os.path.basename(args[0])), causedBy=True)

_logger = logging.getLogger('compilers')
def _checkDirExists(dirpath, message):
	if not os.path.isdir(dirpath):
		_logger.debug(message%dirpath) # legitimate but useful for debugging
	return dirpath

class Compiler(Process):
	"""
	A compiler (of some sort or other)
	"""
	def __init__(self, environs=None):
		Process.__init__(self, environs=environs)
	def compile(self, context, output, src, options, flags=None, includes=None): 
		"""
		output: The object file to create

		src: A list of source file paths

		options: an options dictionary to override global options

		flags: additional flags to pass to the compiler

		includes: a list of include directory paths
		"""
		assert False

class Depends(Process):
	"""
	The command to use to generate a list of dependencies from a list of source files
	"""
	def __init__(self, environs=None):
		Process.__init__(self, environs=environs)
	def depends(self, context, src, options, flags=None, includes=None): 
		"""
		src: A list of source file paths

		options: an options dictionary to override global options

		flags: additional flags to pass to the compiler

		includes: a list of include directory paths
		"""
		assert False

class Linker(Process):
	"""
		Link a set of object files into an executable or a shared library
	"""
	def __init__(self, environs=None):
		Process.__init__(self, environs=environs)
	def link(self, context, output, src, options, shared=False, flags=None, libs=None, libdirs=None):
		"""
		output: The library/executable to create

		src: A list of object file paths

		options: an options dictionary to override global options

		flags: additional flags to pass to the compiler

		libs: A list of libraries to link against

		libdirs: A list of paths to directories that contain libraries
		"""
		assert False

class Archiver(Process):
	"""
	A tool to put a set of object files into an archive for static linking.
	Typically only used on unix.
	"""
	def __init__(self, environs=None):
		Process.__init__(self, environs=environs)
	def archive(self, context, output, src, options): 
		"""
		output: The archive file path to create

		src: A list of source object file paths

		options: an options dictionary to override global options
		"""
		assert False

class ToolChain(object):
	"""
	A collection of compilers, linkers and other tools which represents a complete native tool chain
	"""
	def __init__(self, depends, ccompiler, cxxcompiler, linker, archiver):
		"""
		depends: A Depends object to get a list of dependencies from a list of source files

		ccompiler: A Compiler object for compiling C files

		cxxcompiler: A Compiler object for compiling C++ files

		linker: A Linker object for linking object files to a shared library or executable

		archiver: An Archiver object for making static-link archives
		"""
		assert isinstance(depends, Depends) or depends == None
		self.dependencies = depends
		assert isinstance(ccompiler, Compiler) or ccompiler == None
		self.ccompiler = ccompiler
		assert isinstance(cxxcompiler, Compiler) or cxxcompiler == None
		self.cxxcompiler = cxxcompiler
		assert isinstance(linker, Linker) or linker == None
		self.linker = linker
		assert isWindows() or isinstance(archiver, Archiver) or archiver == None
		self.archiver = archiver

class UnixCompiler(Compiler):
	"""
	A compiler using standard Unix compiler arguments/syntax
	"""
	def __init__(self, command, outputHandler=None, environs=None):
		"""
		command: The path to the compiler
		
		outputHandler: a ProcessOutputHandler to parse the output of the compiler
		"""
		Compiler.__init__(self, environs=environs)
		self.compiler_command = command
		self.compiler_handler = outputHandler or ProcessOutputHandler

	def compile(self, context, output, src, options, flags=None, includes=None):
		args=[
			self.compiler_command,
			'-c',
			'-o', os.path.basename(output)]
		args.extend(['-I%s' % _checkDirExists(x, 'Cannot find include directory ``%s"') for x in (includes or [])])
		args.extend(flags or [])
		args.extend(src)
		self.call(context, args, outputHandler=self.compiler_handler, cwd=os.path.dirname(output), options=options)

defineOption('native.link.wholearchive', None)

class UnixLinker(Linker):
	"""
	A linker using standard Unix linker arguments/syntax
	"""
	def __init__(self, command, outputHandler=None, environs=None):
		"""
		command: The path to the linker
		
		outputHandler: a ProcessOutputHandler to parse the output of the linker
		"""
		Linker.__init__(self, environs=environs)
		self.linker_command = command
		self.linker_handler = outputHandler or ProcessOutputHandler

	def link(self, context, output, src, options, shared=False, flags=None, libs=None, libdirs=None):
		args=[
			self.linker_command,
			'-o', os.path.basename(output)]
		if shared: args.append('-shared')
		args.extend(flags)
		for x in src:
			if x.endswith('.a') and options['native.link.wholearchive']:
				(pref, suff) = options['native.link.wholearchive']
				args.extend([pref, x, suff])
			else:
				args.append(x)
		args.extend(['-L%s' % _checkDirExists(x, 'Cannot find lib directory ``%s"') for x in (libdirs or [])])
		args.extend(['-l%s' % x for x in (libs or [])])
		environs = self.getExpandedEnvirons(context)
		environs['LD_LIBRARY_PATH']=os.pathsep.join(libdirs+[environs.get('LD_LIBRARY_PATH', '')])
		self.call(context, args, outputHandler=self.linker_handler, cwd=os.path.dirname(output), environs=environs, options=options)

class UnixArchiver(Archiver):
	"""
	A archiver using standard Unix archiver arguments/syntax
	"""
	def __init__(self, command, outputHandler=None, environs=None):
		"""
		command: The path to the archiver
		
		outputHandler: a ProcessOutputHandler to parse the output of the archiver
		"""
		Archiver.__init__(self, environs=environs)
		self.ar_command = command
		class ArHandler(ProcessOutputHandler):
			def __init__(self, name, **kwargs):
				ProcessOutputHandler.__init__(self, name, treatStdErrAsErrors=False, **kwargs)
		self.ar_handler = outputHandler or ArHandler
	def archive(self, context, output, src, options):
		args=[
			self.ar_command,
			'-r',
			os.path.basename(output)]
		args.extend(src)
		self.call(context, args, outputHandler=self.ar_handler, cwd=os.path.dirname(output), options=options)

class GccProcessOutputHandler(ProcessOutputHandler):
	"""
	A ProcessOutputHandler than can parse the output of GCC tools
	"""

	#def __init__(self, name, **kwargs):
	#	ProcessOutputHandler.__init__(self, name, **kwargs)
	
	def _decideLogLevel(self, line, isstderr):

		# stderr seems to include all the warnings, notes and other stuff, so can't really use it for error detection

		if re.search(r'error[\s]*([A-Z]+\d+)?:', line, flags=re.IGNORECASE) or (': undefined reference to ' in line): 
			return logging.ERROR
			
		# ignore the contextual lines at the start of errors e.g. ": In function..."
		if (isstderr and not ': In' in line and not line.startswith('In file') and not ': note:' in line) or re.search('warning[\s]*([A-Z]+\d+)?:', line, flags=re.IGNORECASE): return logging.WARNING

		return logging.INFO # default log level
	
	def _parseLocationFromLine(self, line):
		filename = None
		lineno = None
		try:
			filename = re.sub("(.*):([0-9]+): .*", r"\1", line)
			lineno = re.sub("(.*):([0-9]+): .*", r"\2", line)
		except Exception: pass
		return filename, lineno, None, line
	
	def handleEnd(self, returnCode=None):
		# linker failures often have no errors but a really useful message in the first warning, so include that in the error message
		if returnCode and self.getWarnings() and not self.getErrors():
			raise BuildException('%s failed with return code %s (first warning: %s)'%(self._name, returnCode, self.getWarnings()[0]))
		ProcessOutputHandler.handleEnd(self, returnCode=returnCode)


class GCC(ToolChain, UnixCompiler, UnixLinker, Depends):
	"""
	A tool chain based on the GNU Compiler Collection
	"""
	def __init__(self, environs=None): 
		ToolChain.__init__(self, 
			self, 
			UnixCompiler('gcc', GccProcessOutputHandler, environs=environs), 
			self, 
			self, 
			UnixArchiver('ar', environs=environs)
			)
		UnixCompiler.__init__(self, 'g++', GccProcessOutputHandler, environs=environs)
		UnixLinker.__init__(self, 'g++', GccProcessOutputHandler, environs=environs)
		Depends.__init__(self, environs=environs)
	def depends(self, context, src, options, flags=None, includes=None):
		args=[
			'g++', '-M', '-MG',
			'-c']
		args.extend(['-I%s' % x for x in (includes or [])])
		args.extend(flags or [])
		args.extend(src)
		deplist = []

		class GccDependsHandler(ProcessOutputHandler):
			def __init__(self, name, **kwargs):
				ProcessOutputHandler.__init__(self, name, **kwargs)
				self.fatalerrors = []
			def handleLine(self, line, isstderr=False):
				if ': error ' in line: self.fatalerrors.append(line.rstrip())
				if not isstderr and line.startswith(' '):
					# sometimes there are multiple items on a single line, space delimited
					# if there are spaces in the path itself they are escaped as "\ "
					deplist.extend([x.replace('<space>',' ') for x in line.strip('\\').strip().replace('\\ ','<space>').split(' ')])
			def handleEnd(self, returnCode=None):
				if returnCode and not self.getErrors() and self.fatalerrors:
					# special-case to give a more useful error message tha just the exit code if a dependency is missing
					raise BuildException('Native dependency checking failed: %s'%(self.fatalerrors[0]))
				return super(GccDependsHandler, self).handleEnd(returnCode=returnCode)

		try:
			self.call(context, args, outputHandler=GccDependsHandler, options=options)
		except Exception, e:
			# occasionally we see SIGABRT (=6) for no reason (e.g. on ARM), so do a retry
			if 'return code -6' not in str(e): raise
			_logger.warn('g++ dependency checking failed, may be transient so will retry: %s', e)
			time.sleep(15)
			del deplist[:]
			self.call(context, args, outputHandler=GccDependsHandler, options=options)

		return deplist

class VisualStudioProcessOutputHandler(ProcessOutputHandler):
	"""
	A ProcessOutputHandler that can parse the output of Visual Studio tools
	"""
	def _decideLogLevel(self, line, isstderr):
		if isstderr or re.search(r'error[\s]*([A-Z]+\d+)?:', line, flags=re.IGNORECASE): 
			level = logging.ERROR
			
			transientRegex = self.options.get('visualstudio.transientErrorRegex',None)
			if transientRegex and re.match(transientRegex, line): 
				self._transientError = line
				return logging.WARNING # avoid reporting an error unless the target actually fails
			
			if 'fatal error C1903: unable to recover from previous error' in line and self.getErrors():
				level = logging.INFO # this is the same error not a new one
			
		elif re.search('warning[\s]*([A-Z]\d+)?:', line, flags=re.IGNORECASE): 
			level = logging.WARNING
		else:
			level = logging.INFO # default log level
			
			# heuristic to make context printed after the error/warn message 
			# available in error messages; might be worth revamping this to 
			# put entire error into one line			
			if getattr(self, '_previousLogLevel', None) in [logging.ERROR, logging.WARNING] and 'note: see' in line:
				self._appendToMessage = ' - caused previous error/warning - %s'%(self._previousLogLine)
				return self._previousLogLevel
			
		self._previousLogLevel = level
		self._previousLogLine = line
		self._appendToMessage = None
		return level

	def _preprocessLine(self, line): 
		if getattr(self, '_appendToMessage', None):
			return line+self._appendToMessage
		return line

	def _parseLocationFromLine(self, line):
		filename = None
		lineno = None
		colno = None
		try:
			# expecting format
			#<location>: <category> <number>: <description>
			# where location = <string> or <path>(line) or <path>(line-line) or <path>(line,col) or <path>(line,col-col)
			# TODO: add colno support
			m = re.match(r'(([a-zA-Z]:)?[^:]+)[(]([0-9]+)[^:]*:(.*)', line)
			if m:
				filename = m.group(1).replace('/','\\')
				lineno = m.group(3)
				line = m.group(4).strip() + ' - at '+line[:line.find(m.group(4))].strip().strip(':').strip()
			else:
				m = re.match(r'([^(]+)[(]([0-9]+)[^:]*:(.*)', line)
		except Exception: pass
		return filename, lineno, colno, line

def __testVisualStudioOutputHandler():
	# tricky to do with doctesting due to escaping issues
	h = VisualStudioProcessOutputHandler('cl.exe')
	x = h._parseLocationFromLine(r'c:\foo\bar(123): error C456: descr')
	assert x == (r'c:\foo\bar', '123', None, r'error C456: descr - at c:\foo\bar(123)'), x

	x = h._parseLocationFromLine(r'D:\foo\bar(123,45-67): warning C456: descr')
	assert x == (r'D:\foo\bar', '123', None, r'warning C456: descr - at D:\foo\bar(123,45-67)'), x

	x = h._parseLocationFromLine(r'\\unc\foo\bar(123,45-67): warning C456: descr')
	assert x == (r'\\unc\foo\bar', '123', None, r'warning C456: descr - at \\unc\foo\bar(123,45-67)'), x

	x = h._parseLocationFromLine(r'c:\program files (x86)\foo\bar(123,45-67): warning C456: descr')
	assert x == (r'c:\program files (x86)\foo\bar', '123', None, r'warning C456: descr - at c:\program files (x86)\foo\bar(123,45-67)'), x
__testVisualStudioOutputHandler()

defineOption('visualstudio.liboutput', None)
defineOption('visualstudio.pdboutput', None)
# errors matching this will not be logged as an ERROR the first time they occur and will result in a retry
defineOption('visualstudio.transientErrorRegex', '.*(Permission denied|Access denied).*')
defineOption('visualstudio.transientErrorRetrySecs', 40)
defineOption('visualstudio.outputHandlerFactory', VisualStudioProcessOutputHandler)
"""Allows overriding the output handler used by Visual Studio for compiler output such as errors and warnings. """

class VisualStudio(Compiler, Linker, Depends, Archiver, ToolChain):
	"""
	A ToolChain representing using Visual Studio compilers et al
	"""
	def __init__(self, vsbin):
		self.vsbin = vsbin
		ToolChain.__init__(self, self, self, self, self, self)
		Linker.__init__(self)
		Depends.__init__(self)
		Compiler.__init__(self)
		Archiver.__init__(self)
	def call(self, *args, **kwargs):
		try:
			super(VisualStudio, self).call(*args, **kwargs)
		except BuildException, e:
			options = kwargs.get('options',{})
			transientRegex = options.get('visualstudio.transientErrorRegex', None)
			if not (transientRegex and re.match(transientRegex, str(e))):
				raise e
			# seen occasionally. may be due to POSIX and Win32 API file operations 
			# remaining out of sync for a short time after a file is written on windows
			# nb: it would be nice to find a way to prevent the already-logged error 
			# from making it look like there's a build failure in the case where 
			# this retry succeeds
			_logger.warn('Build step failed, may be transient so will retry: %s', e)
			time.sleep(options.get('visualstudio.transientErrorRetrySecs', 10))
			super(VisualStudio, self).call(*args, **kwargs)
				
	def compile(self, context, output, src, options, flags=None, includes=None):
		args=[
			r"%s\cl.exe" % self.vsbin,
			'-c',
			'/Fo'+os.path.basename(output)]
		args.extend(['-I%s' % _checkDirExists(x.replace('/','\\'), 'Cannot find include directory ``%s"') for x in (includes or [])])
		args.extend(flags or [])
		args.extend(src)
		self.call(context, args, outputHandler=options.get('visualstudio.outputHandlerFactory', None) or VisualStudioProcessOutputHandler, cwd=os.path.dirname(output), environs={'PATH':os.pathsep.join(options['native.cxx.path'])}, options=options)
	def link(self, context, output, src, options, shared=False, flags=None, libs=None, libdirs=None):
		args=[r"%s\link.exe" % self.vsbin]
		if shared: 
			args.append('/DLL')
			args.append('/INCREMENTAL:NO')
		if options['visualstudio.liboutput']:
			args.append('/OUT:'+output)
			args.append('/IMPLIB:'+options['visualstudio.liboutput'])
		else:
			args.append('/OUT:'+os.path.basename(output))
		if options['visualstudio.pdboutput']:
			args.append('/PDB:'+options['visualstudio.pdboutput'])
		args.extend(flags)
		args.extend(['/LIBPATH:%s' % _checkDirExists(x.replace('/','\\'), 'Cannot find lib directory ``%s"') for x in (libdirs or [])])
		args.extend(['%s.lib' % x for x in (libs or [])])
		args.extend(src)
		self.call(context, args, outputHandler=options.get('visualstudio.outputHandlerFactory', None) or VisualStudioProcessOutputHandler, cwd=os.path.dirname(output), environs={'PATH':os.pathsep.join(options['native.cxx.path'])}, options=options)
	def archive(self, context, output, src, options):
		args=[r"%s\lib.exe" % self.vsbin, '/OUT:'+os.path.basename(output), '/nologo']
		args.extend(src)
		self.call(context, args, outputHandler=options.get('visualstudio.outputHandlerFactory', None) or VisualStudioProcessOutputHandler, cwd=os.path.dirname(output), environs={'PATH':os.pathsep.join(options['native.cxx.path'])}, options=options)

	def depends(self, context, src, options, flags=None, includes=None):
		args=[
			r"%s\cl.exe" % self.vsbin,
			'/Zs', '/showIncludes',
			'-c']
		args.extend(['-I%s' % _checkDirExists(x.replace('/','\\'), 'Cannot find include directory ``%s"') for x in (includes or [])])
		args.extend(flags or [])
		args.extend(src)
		deplist = list(src)
		fatalerrors = []

		class VSDependsHandler(VisualStudioProcessOutputHandler):
			def handleLine(self, line, isstderr=False):
				data = line.encode('utf8')
				if 'fatal error' in data: fatalerrors.append(data.strip())
				if 'Cannot open include file:' in data:
					data = re.sub(".*Cannot open include file: '([^']*)':.*", r'\1', data).strip()
					if data: deplist.append(data)
				elif 'Note: including file:' in data:
					data = re.sub(".*Note: including file:", '', data).strip()
					if data: deplist.append(data)
				else:
					VisualStudioProcessOutputHandler.handleLine(self, line, isstderr=isstderr)
			def _decideLogLevel(self, line, isstderr):
				l = VisualStudioProcessOutputHandler._decideLogLevel(self, line, isstderr)
				if l < logging.ERROR: l = logging.DEBUG # don't care about compiler warnings etc at dep generation time
				return l
				
			def handleEnd(self, returnCode=None):
				if returnCode and not self.getErrors() and fatalerrors:
					# special-case to give a more useful error message tha just the exit code if a dependency is missing
					raise BuildException('Native dependency checking failed: %s'%(fatalerrors[0]))
				return super(VSDependsHandler, self).handleEnd(returnCode=returnCode)

		self.call(context, args, outputHandler=VSDependsHandler, options=options)
		return deplist

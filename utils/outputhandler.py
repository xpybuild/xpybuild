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
# $Id: outputhandler.py 301527 2017-02-06 15:31:43Z matj $
# Authors: Ben Spiller
#

import subprocess, os, re, logging
from buildexceptions import BuildException


# we might want a wrapper that stores all content and writes it to a file for artifact publishing, 
# perhaps only iff an exception occurs and/or its not empty


class ProcessOutputHandler(object):
	"""
	An extensible class for handling stdout/stderr output lines and return code 
	from a process, accumulating error and warnings, and converting into 
	appropriate log statements and a summary exception if it failed. 
	
	It is expected that subclasses would be created to abtract away handling of 
	output from different particular types of process (e.g. Java compilation, 
	gmake, msbuild, etc).
	
	Usage: the handleLine method will be invoked for every line in the stdout 
	and stderr, then handleEnd will be called once, with the process returnCode 
	if known. handleEnd should raise a BuildException if the process is 
	deemed to have failed. 
	
	The errors and warnings lists can be inspected after handleEnd has been 
	called to get further information if desired. 
	
	Subclasses may often wish to do some of the following:
		- override the logic for deciding what consistutes an error/warning 
			(see _decideLogLevel)
		- use a regex to get the filename and number from error messages to 
			support IDE jump-to integration (see _parseLocationFromLine)
		- strip timestamp/threadid prefixes from lines (see _preprocessLine) 
		- support warnings-as-errors behaviour by putting the first warning into 
			the final error message if the only error is that there are warnings 
			(by overriding handleEnd)
	
	This class is not thread-safe, so locking should be provided by the caller 
	if multiple threads are in use (e.g. for reading stdout+err in parallel). 
	
	"""
	def __init__(self, name, treatStdErrAsErrors=True, **kwargs):
		"""
		The constructor for this object. Subclasses that override this should 
		always pass **kwargs down to the super constructor to allow for new 
		functionality to be added
		
		@param name: a short display name for this process or target, used as a 
		prefix for log lines. 
		
		@param treatStdErrAsErrors: controls where all content on stderr 
		(rather than stdout) is treated as an error by default. The correct 
		setting depends on how the process being invoked uses stdout/err. 
		
		@keyword options: a dictionary of resolved option values, in case aspects 
		of this handler are customizable. Available to implementastions as 
		self.options (if None is passed, self.options will be an empty 
		dictionary)
		"""
		self._name = name
		self._errors = []
		self._warnings = []
		
		self._logger = logging.getLogger('process.%s'%name)
		self._treatStdErrAsErrors = treatStdErrAsErrors
		self.options = kwargs.pop('options', None) or {}
		assert not kwargs, 'Unexpected keyword argument to ProcessOutputHandler: %s'%kwargs.keys()
	
	def handleLine(self, line, isstderr=False):
		"""
		Called once for every line in the stdout and stderr 
		(stderr after, if not during stdout). 
		
		If possible, line should be a unicode object rather than a byte string. 
		
		The default implementation uses _decideLogLevel to decide how to 
		interpret each line, then calls _preprocessLine and _parseLocationFromLine 
		on the line before stashing errors/warnings, and passing the 
		pre-processed line to _log for logging at the specified level. 
		
		@param isstderr: if stdout/err are segregated then this can be used as a 
		hint to indicate the source of the line. 
		"""
		level = self._decideLogLevel(line, isstderr)
		if not level: return
		
		if level >= logging.WARNING or self._logger.isEnabledFor(level):
			line = self._preprocessLine(line)
			try:
				filename, fileline, col, line = self._parseLocationFromLine(line)
			except Exception:
				filename, fileline = self._parseLocationFromLine(line) # old form, for backwards compat
				col = None
			
			if level == logging.ERROR:
				self._errors.append(line)
			elif level == logging.WARNING:
				self._warnings.append(line)
			self._log(level, line, filename, fileline, col)
	
	def handleEnd(self, returnCode=None):
		if self._warnings: self._logger.warning('%d warnings during %s', len(self._warnings), self._name)
			
		if self._errors: 
			msg = self._errors[0]
			if len(self._errors)>1:
				msg = '%d errors, first is: %s'%(len(self._errors), msg)
		elif returnCode:
			msg = '%s failed with return code %s'%(self._name, returnCode)
			# in case it's relevant, since the return code doesn't provide much to go on
			if self._warnings: msg += '; no errors reported, first warning was: %s'%self._warnings[0]
		else:
			return
		raise BuildException(msg)
	
	def _decideLogLevel(self, line, isstderr):
		"""
		Used by the default handleLine implementation to 
		decide whether the specified (raw, not yet pre-processed) line is a 
		warning, an error, or else whether it should be logged at INFO/DEBUG 
		or not at all. Called exactly once per line. 
		
		The default implementation uses "error[\s]*([A-Z]\d+)?:" to check for 
		errors (similarly for warnings), and logs everything else only at INFO, 
		and also treats all stderr output as error lines. 
		
		Typically returns logging.ERROR, logging.WARNING, logging.DEBUG/INFO or 
		None. 
		"""
		
		assert isinstance(line, unicode) # only accept unicode - force caller to explicitly decode their output before calling this, e.g. l.decode(getStdoutEncoding())
		
		if (isstderr and self._treatStdErrAsErrors) or re.search(r'error[\s]*([A-Z]+\d+)?:', line, flags=re.IGNORECASE): return logging.ERROR
		if re.search('warning[\s]*([A-Z]+\d+)?:', line, flags=re.IGNORECASE): return logging.WARNING
		return logging.INFO # default log level
	
	def _parseLocationFromLine(self, line):
		"""
		Return (filename, linenumber, col, line)
		
		For backwards compat, returning (filename,location) is also permitted
		
		The returned line may be identical to the input, or may have the filename stripped off.
		
		linenumber is a string and may be a simple line number or may be a "lineno,col" string. 
		
		"""
		return None,None,None,line
	
	def _log(self, level, msg, filename=None, fileline=None, filecol=None):
		""" Writes the specified msg to the logger. 
		
		If filename and fileline are specified, they are passed to the logrecord, 
		which allows output formatting customizations. 
		"""
		if level == logging.ERROR:
			pattern = '%s ERROR> %s'
		elif level == logging.WARNING:
			pattern = '%s WARN> %s'
		else:
			pattern = '%s> %s'
		r = self._logger.makeRecord(self._logger.name, level, filename, fileline, 
			pattern, (self._name, msg), exc_info=None, func=self._name)
		# overriding python's filename/line as above is a bit dodgy and doesn't support columns either, 
		# so as first choice set some xpybuild-specific attributes onto the LogRecord
		if filename: 
			r.xpybuild_filename = filename
			if fileline:
				r.xpybuild_line = fileline
			if filecol:
				r.xpybuild_col = filecol
		self._logger.handle(r)

	def _preprocessLine(self, line): 
		""" 
		Performs any necessary transformations on the line before it is 
		logged or stored. By default it strips() whitespace. 
		
		This can be overridden to add support for stripping 
		timestamps, thread ids, unwanted indentation, etc. 
		"""
		return line.strip()
	
	def getErrors(self): return self._errors
	def getWarnings(self): return self._warnings
	
class StdoutRedirector(ProcessOutputHandler):
	""" Redirects stdout to a file verbatim and reports errors on stderr """
	def __init__(self, name, fd, **kwargs):
		""" 
		fd is a binary-mode writable file descriptor """
		ProcessOutputHandler.__init__(self, name, True, **kwargs)
		self.fd = fd
	
	def handleLine(self, line, isstderr=False):
		if isstderr:
			ProcessOutputHandler.handleLine(self, line, isstderr)
		else:
			self.fd.write(line.encode("UTF-8")+os.linesep)
	
	def handleEnd(self, returnCode=None):
		ProcessOutputHandler.handleEnd(self, returnCode)

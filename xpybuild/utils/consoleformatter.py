# xpyBuild - eXtensible Python-based Build System
#
# Handlers for formatting stdout
#
# Copyright (c) 2015 - 2019 Software AG, Darmstadt, Germany and/or its licensors
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
# $Id: consoleformatter.py 397881 2022-01-20 17:40:49Z bsp $
#

"""
Pluggable classes for customizing the format that xpybuild uses when writing log messages to stdout (for example, 
for Teamcity, make, Visual Studio, etc). 
"""

import logging, os, time
import re

_artifactsLog = logging.getLogger('xpybuild.artifacts')
# keep track of formatters that have been instantiated to allow us to publish artifacts to them
_outputFormattersInUse = []

_registeredConsoleFormatters = {}

class ConsoleFormatter(object):
	"""
	Base class for customizing the format used 
	for handling log records when displaying to the command console/stdout. 
	
	This allows to output to be customized for the tool that is executing 
	xpybuild, for example e.g. teamcity, visual studio IDE, etc. 
	
	Use self.fmt.format(record) to format the message including (multi-line) python 
	exception traces.

	This class is only used for stdout, it does not affect the format used 
	to write messages to the on-disk xpybuild log file. 

	"""

	level = logging.ERROR
	
	def __init__(self, output, buildOptions, **kwargs):	
		"""
		@param output: The output stream, which can cope with unicode characters. 
		@param buildOptions: Dictionary of build options
		"""
		super().__init__()
		self.output = output
		self.fmt = logging.Formatter()
		self.bufferingDisabled = False # can be set to True to prevent it for handlers for which it's not appropriate
		self.bufferingRequired = False # can be set to True to require it for handlers where it's essential for correctness (when a target is retried) e.g. TeamCity CI
		_outputFormattersInUse.append(self)
		
	def setLevel(self, level):
		self.level = level
	def handle(self, record):
		raise NotImplementedError("Not Implemented")
	
	def publishArtifact(self, logger, displayName, path):
		""" Publishes the specified local path (e.g. a log file) as an artifact, 
		if supported by this formatter. 
		
		The default implementation used by most formatters is a no-op. 

		@param logger: The logger instance that should be used to write any 
		messages to stdout as part of the publishing process (this will not be
		relevant for all formatters). 
		
		@param displayName: A string describing the artifact being published. 
		Some output formatters may ignore this string. 
		
		@param path: An absolute path to a file (e.g. a log file) that should 
		be published. Never equal to empty or None. 
		"""
		pass
		

def registerConsoleFormatter(name: str, handler: ConsoleFormatter):
	"""
	Make a custom console formatter class available for use by xpybuild. 
	"""
	_registeredConsoleFormatters[name] = handler

def publishArtifact(displayName, path):
	""" Publishes the specified local path as an artifact, 
	if supported by the configured output format. 
	
	For example this can be used to publish log and error output if a target 
	fails. 
	
	Note that many output formatters do not have any concept of artifact 
	publishing, so it is usually desirable to log important paths at INFO 
	or WARN/ERROR or above in addition to calling this method. 
	
	@param displayName: A string describing the artifact being published. 
	Some output formatters may ignore this string. 
	
	@param path: An absolute path to a file (e.g. a log file) that should 
	be published, if supported. Empty string or None are ignored. 
	"""
	if not path:
		_artifactsLog.debug('Ignoring empty artifact path: "%r"', path)
		return
	
	assert displayName, 'displayName must be specified'
	
	# we do error checking at this level so we can detect errors regardless 
	# of what output formatter is configured
	
	if not path or not os.path.isabs(path):
		raise Exception('Cannot publish artifact path "%s" because only absolute paths are supported'%path)

	path = os.path.normpath(path)
	
	if not os.path.exists(path):
		_artifactsLog.warning("Cannot find path for artifact publishing: \"%s\"", path)
	# always log at debug, so they're there 
	_artifactsLog.debug('Publishable artifact path for %s: "%s"', displayName, path)

	for f in _outputFormattersInUse:
		f.publishArtifact(_artifactsLog, displayName, path)

class DefaultConsoleFormatter(ConsoleFormatter):
	"""
	The default text output formatter for xpybuild. 
	"""
	def __init__(self, stream, buildOptions, **kwargs):
		ConsoleFormatter.__init__(self, stream, buildOptions, **kwargs)
		self.delegate = logging.StreamHandler(stream)
		self.delegate.setFormatter(logging.Formatter('[%(threadName)4s] %(message)s', None))
		self.lastDepTime = time.time()
	def handle(self, record):
		# since dependency resolution is usually quick, throttle logging to 
		# once per second
		if record.levelno == logging.CRITICAL:
			msg = record.getMessage()
			if msg.startswith('***') and 'Resolving dependencies for' in msg:
				if self.lastDepTime and time.time()>self.lastDepTime+1:
					self.lastDepTime = time.time()
				else:
					return # no-op

		self.delegate.handle(record)
	def setLevel(self, level):
		ConsoleFormatter.setLevel(self, level)
		self.delegate.setLevel(level)

class TeamcityHandler(ConsoleFormatter):
	"""
	ConsoleFormatter that writes progress and error messages in a format suitable 
	for Teamcity CI, and can publish artifacts such as build logs to Teamcity. 
	"""
	def __init__(self, output, buildOptions, **kwargs):
		ConsoleFormatter.__init__(self, output, buildOptions, **kwargs)
		
		self.bufferingRequired = True # need buffering so that we can stop errors being written out if the target subsequently succeeds on retry
		
	@staticmethod
	def teamcityEscape(s):
		# to be on the safe side, remove all non-ascii chars
		s = s.encode('ascii', errors='replace').decode('ascii')
		
		s = s.replace('\r','').strip()
		s = s.replace('|', '||')
		s = s.replace("'", "|'")
		s = s.replace('[', '|[')
		s = s.replace(']', '|]')
		s = s.replace('\n', '|n')
		return s
	
	def handle(self, record):
		if record.getMessage().startswith("##teamcity"):
			self.output.write("%s\n" % record.getMessage())
		elif record.levelno == logging.ERROR:
			self.output.write("##teamcity[message text='%s' status='ERROR']\n" % TeamcityHandler.teamcityEscape(self.fmt.format(record)))
		elif record.levelno == logging.CRITICAL and record.getMessage().startswith("***"):
			self.output.write("##teamcity[progressMessage '%s']\n" % TeamcityHandler.teamcityEscape(self.fmt.format(record)))
		else:
			self.output.write("##teamcity[message text='%s']\n" % TeamcityHandler.teamcityEscape(self.fmt.format(record)))
		self.output.flush()
	
	def publishArtifact(self, logger, displayName, path):
		# displayName is ignored for teamcity
		logger.critical("##teamcity[publishArtifacts '%s']" % TeamcityHandler.teamcityEscape(path))

registerConsoleFormatter("teamcity", TeamcityHandler)

class MakeConsoleFormatter(ConsoleFormatter):
	"""
	ConsoleFormatter that logs in a format that matches GNU Make. 

	Output format::
  	
		file:line: category: description

	"""
	def handle(self, record):
		if record.levelno == logging.ERROR:
			category = 'error'
		elif record.levelno == logging.WARNING:
			category = 'warning'
		else:
			category = None
	
		if record.name in ["scheduler"]:
			location = "xpybuild"
		elif record.pathname == None:
			location = record.funcName
		else:
			location = "%s:%s" % (record.pathname, record.lineno or 0)

		if category:
			self.output.write("%s: %s: %s\n" % (location, category, self.fmt.format(record)))
		else:
			self.output.write("%s\n" % self.fmt.format(record))

		self.output.flush()


registerConsoleFormatter("make", MakeConsoleFormatter)


class VisualStudioConsoleFormatter(ConsoleFormatter):
	"""
	ConsoleFormatter than writes warnings, errors and file locations in a format 
	that Visual Studio can parse.

	Required Format::

		<location>: <category> <number>: <description>

	where:
		- category = warning or error
		- number = specific error or warning number
		- location = <string> or <path>(line) or <path>(line-line) or <path>(line,col) or <path>(line,col-col)
		- description = free-form string

	"""
	output = None
	def handle(self, record):
		if record.levelno == logging.ERROR:
			category = 'error'
		elif record.levelno == logging.WARNING:
			category = 'warning'
		else:
			category = 'info'
	
		filename = getattr(record, 'xpybuild_filename', record.pathname)
		lineno = getattr(record, 'xpybuild_line', record.lineno or 0)
		col = getattr(record, 'xpybuild_col', 0)
		if record.name in ["scheduler"] and (not filename or filename.endswith('scheduler.py')):
			location = "xpybuild"
		elif not filename:
			location = record.funcName
		else:
			location = "%s(%s%s)" % (filename.replace('/','\\'), lineno, ',%s'%col if col else '') # try to provide column info if we have it

		errno = record.funcName

		msg = self.fmt.format(record)
		if re.search('(WARN|ERROR)[>] (warning|error).*:', msg):
			# the message already starts with the level (and maybe error code) so just strip off our prefix leaving the VS prefix
			msg = msg[msg.find('>')+1:].strip()
		else:
			# probably not a cl.exe output line, so add a VS prefix so it shows up right
			msg = "%s %s: %s" % (category, errno, msg)
			
		self.output.write("%s : %s\n" % (location, msg))

		self.output.flush()


registerConsoleFormatter("visualstudio", VisualStudioConsoleFormatter)

registerConsoleFormatter("default", DefaultConsoleFormatter)

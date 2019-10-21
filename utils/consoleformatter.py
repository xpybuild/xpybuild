# xpyBuild - eXtensible Python-based Build System
#
# Handlers for formatting stdout
#
# Copyright (c) 2015 - 2017 Software AG, Darmstadt, Germany and/or its licensors
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
# $Id: ConsoleFormatters.py 301527 2017-02-06 15:31:43Z matj $
#

import logging, os, time

_artifactsLog = logging.getLogger('xpybuild.artifacts')
# keep track of formatters that have been instantiated to allow us to publish artifacts to them
_outputFormattersInUse = []
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

class ConsoleFormatter(object):
	"""
	An xpybuild-specific base class for customizing how log output is formatted 
	for output to the command console/stdout. 
	
	This allows to output to be customized for the tool that is executing 
	xpybuild, for example e.g. teamcity, visual studio IDE, etc. 
	
	Use self.fmt.format(record) to format the message including (multi-line) python 
	exception traces.

	This class is only used for stdout, it does not affect the format used 
	to write messages to the on-disk xpybuild log file. 

	"""

	level = logging.ERROR
	
	def __init__(self):
		self.fmt = logging.Formatter()
		self.bufferingDisabled = False # can be set to True to prevent it for handlers for which it's not appropriate
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
		

class DefaultConsoleFormatter(ConsoleFormatter):
	"""
	The default text output formatter for xpybuild. 
	"""
	def __init__(self, stream, buildOptions):
		ConsoleFormatter.__init__(self)
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

_registeredConsoleFormatters = {}

def registerConsoleFormatter(name, handler):
	"""
	Called to make a custom console formatter class available for use by xpybuild. 
	"""
	_registeredConsoleFormatters[name] = handler

registerConsoleFormatter("default", DefaultConsoleFormatter)

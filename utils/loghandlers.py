# xpyBuild - eXtensible Python-based Build System
#
# log formatting handlers
#
# Copyright (c) 2015 - 2017 Software AG, Darmstadt, Germany and/or its licensors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# $Id: loghandlers.py 301527 2017-02-06 15:31:43Z matj $
#

import logging

class LogHandler(object):
	"""
	An xpybuild-specific base class for customizing log output for specific 
	formats e.g. teamcity, visual studio IDE, etc
	
	Use self.fmt.format(record) to format the message including (multi-line) python 
	exception traces.
	"""

	level = logging.ERROR
	
	def __init__(self):
		self.fmt = logging.Formatter()
		self.bufferingDisabled = False # can be set to True to prevent it for handlers for which it's not appropriate

		
	def setLevel(self, level):
		self.level = level
	def handle(self, record):
		raise "Not Implemented"

class XpybuildHandler(LogHandler):
	def __init__(self, stream, buildOptions):
		LogHandler.__init__(self)
		self.delegate = logging.StreamHandler(stream)
		self.delegate.setFormatter(logging.Formatter('[%(threadName)4s] %(message)s', None))
	def handle(self, record):
		self.delegate.handle(record)
	def setLevel(self, level):
		LogHandler.setLevel(self, level)
		self.delegate.setLevel(level)

_handlers = {}

def registerHandler(name, handler):
	_handlers[name] = handler

registerHandler("xpybuild", XpybuildHandler)

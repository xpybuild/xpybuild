# xpyBuild - eXtensible Python-based Build System
#
# File wrapper that buffers output until the end of the current target so that 
# all related lines are displayed in order
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
# $Id: outputbuffering.py 301527 2017-02-06 15:31:43Z matj $
#


import threading, re, os, time
import locale
from threading import Lock

from xpybuild.utils.consoleformatter import registerConsoleFormatter, ConsoleFormatter
from xpybuild.utils.terminal import getTerminalSize

class OutputBufferingManager(object):
	"""
	Singleton class that manages whether buffering is currently enabled for 
	the current thread and makes the buffering wrappers dump their buffered 
	content at the end. 
	"""
	def __init__(self):
		self.__tlocal = threading.local()
		self.__wrappers = []

	def isBufferingEnabledForCurrentThread(self):
		""" Returns true if a wrapper is (optionally) allowed to buffer 
		log content from the current thread. 
		"""
		return getattr(self.__tlocal, 'enabled', False)
	
	def startBufferingForCurrentThread(self):
		""" Enable buffering by all supported wrappers for this thread 
		until endBufferingForCurrentThread is called. 
		
		Thsi is idempotent. There is no ref counting. 
		"""
		self.__tlocal.enabled = True
		
	def endBufferingForCurrentThread(self):
		""" End buffering. This is idempotent and can be safely called 
		even if it was not started. """
		if not self.isBufferingEnabledForCurrentThread(): return
		
		self.__tlocal.enabled = False
		for w in self.__wrappers:
			w.writeBufferedMessages()
	
	def registerStreamWrapper(self, w):
		self.__wrappers.append(w)
	
outputBufferingManager = OutputBufferingManager()

class OutputBufferingStreamWrapper(object):
	"""
	Thread-safe class that adds buffering for current thread (if currently 
	enabled). Buffered messages will be written when 
	outputBufferingManager.endBufferingForCurrentThread() is called.
	
	Writes characters not bytes. 
	"""
	def __init__(self, underlying, bufferingDisabled=False):
		self.__underlying = underlying
		self.tlocal = threading.local()
		outputBufferingManager.registerStreamWrapper(self)
		self.bufferingDisabled = bufferingDisabled # can be set by formatter if doesn't support it, e.g. progress
	
	def __writeUnderlying(self, s):
		try:
			self.__underlying.write(s)
		except Exception:
			# add replacement characters for anything that isn't supported by this encoding
			encoding = self.__underlying.encoding or locale.getpreferredencoding()
			self.__underlying.write(s.encode(encoding, errors='replace').decode(encoding, errors='replace'))

	
	def write(self, s):
		if not self.bufferingDisabled and outputBufferingManager.isBufferingEnabledForCurrentThread():
			self.tlocal.buffer = getattr(self.tlocal, 'buffer', '')+s
		else:
			self.__writeUnderlying(s)
				
	def flush(self):
		self.__underlying.flush()

	def writeBufferedMessages(self):
		buf = getattr(self.tlocal, 'buffer', '')
		if buf:
			self.__writeUnderlying(buf)
			self.tlocal.buffer = ''
			self.flush() # probably overdue a flush by now
	

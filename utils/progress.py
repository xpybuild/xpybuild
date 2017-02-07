# xpyBuild - eXtensible Python-based Build System
#
# logging handler that logs progress messages as a progress bar
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
# $Id: progress.py 301527 2017-02-06 15:31:43Z matj $
#

# ##teamcity[progressMessage '(%d/%d) %s']

import logging, re, os, time

from buildcommon import *

from utils.loghandlers import registerHandler, LogHandler
from threading import Lock
from utils.terminal import getTerminalSize

class ProgressBarHandler(LogHandler):
	"""
	An alternative log handler that outputs as a non-coloured progress bar 
	for systems without cursor movement support
	"""
	output = None
	state = "OK"
	progress = False
	width = None
	mutex = Lock()
	spinning = False
	spinner = '/'
	time = 0
	timethreshold = 0

	def __init__(self, output, buildOptions):
		self.output = output
		self.bufferingDisabled = True # buffering isn't helpful in progress mode
		(self.width, height) = getTerminalSize()
		self.width = self.width - len("Progress: [] (xxx/xxx)  ")
		try:
			self.timethreshold = int(os.environ.get("XPYBUILD_PROGRESS_RATE", 0.0))
		except:
			pass

	def getSymbol(self):
		if self.state == "OK": return "="
		elif self.state == "WARN": return "#"
		elif self.state == "ERROR": return "!"

	def occupied(self, current, total):
		return (current*self.width) / total

	def unoccupied(self, current, total):
		return self.width - (current*self.width) / total

	def getNextSpinner(self):
		if self.spinner == '/':
			self.spinner = '-'
		elif self.spinner == '-':
			self.spinner = '\\'
		elif self.spinner == '\\':
			self.spinner = '|'
		elif self.spinner == '|':
			self.spinner = '/'
		return self.spinner		

	def handle(self, record):
		with self.mutex:
			if record.levelno == logging.WARN:
				if self.state == "OK": self.state = "WARN"
			elif record.levelno == logging.ERROR:
				self.state = "ERROR"
			elif record.levelno == logging.CRITICAL and re.match("^\\*\\*\\* *[0-9]*/[0-9]* ", record.getMessage()):
				self.progress = True
				try:
					if time.time()-self.time < self.timethreshold: return
				
					current = int(re.sub('([0-9]*)/([0-9]*) .*', '\\1', record.getMessage()[3:]))
					total = int(re.sub('([0-9]*)/([0-9]*) .*', '\\2', record.getMessage()[3:]))


					self.output.write("\r")
					self.output.write("Progress: [")
					symbol = self.getSymbol()
					for i in range(0, self.occupied(current, total)):
						self.output.write(symbol)
					for i in range(0, self.unoccupied(current, total)):
						self.output.write(" ")
					self.output.write('] (%3d/%3d)' % (current, total))
					if current == total:
						self.progress = False
						self.spinning = False
					self.time = time.time()
				except Exception as e:
					self.output.write("\r%s\n" % e)
				self.output.flush()
			elif record.levelno == logging.CRITICAL and re.match("^\\*\\*\\* XPYBUILD", record.getMessage()):
				self.progress = False
				self.spinning = False
				for l in record.getMessage().split('\n'):
					self.output.write('\r'+l.rstrip())
					for i in range(0, self.width+23-len(l)):
						self.output.write(" ")
					self.output.write('\n')
				self.output.flush()
			elif record.levelno == logging.CRITICAL and re.match("^\\*\\*\\*", record.getMessage()):
				self.spinning = True
				try:
					if time.time()-self.time < self.timethreshold: return
					self.output.write("\r")
					self.output.write("Progress: ["+self.getNextSpinner()+"]")
					for i in range(0, self.width+len(" (xxx/xxx)")):
						self.output.write(" ")
				except Exception as e:
					self.output.write("\r%s\n" % e)
				self.output.flush()
			else:
				if not self.progress and not self.spinning:
					self.output.write('\r'+record.getMessage().rstrip())
					for i in range(0, self.width+23-len(record.getMessage())):
						self.output.write(" ")
					self.output.write('\n')
					self.output.flush()

class VT100ProgressBarHandler(LogHandler):
	"""
	An alternative log handler that outputs as a coloured progress bar
	"""
	output = None
	state = "OK"
	progress = False
	width = None
	fullwidth = None
	mutex = Lock()
	spinning = False
	spinner = '/'
	time = 0
	timethreshold = 0

	def __init__(self, output, buildOptions):
		self.output = output
		self.bufferingDisabled = True # buffering isn't helpful in progress mode
		self.workers = buildOptions['workers']
		self.saveCursor()
		self.output.write('\n')
		for i in range(1, self.workers+1):
			self.clearLine()
			self.output.write('Progress B-%02d: [\n' % i)
		self.output.flush()
		self.cursorUp(self.workers+1)
		(self.fullwidth, height) = getTerminalSize()
		self.width = self.fullwidth - len("Progress B-00: [] (xxx/xxx)  ")
		try:
			self.timethreshold = int(os.environ.get("XPYBUILD_PROGRESS_RATE", 0.0))
		except:
			pass

	def getNoColour(self):
		return '\033[0m'
	def getColour(self):
		if self.state == "OK":
			return '\033[1;32m'
		elif self.state == "WARN":
			return '\033[1;33m'
		elif self.state == "ERROR":
			return '\033[1;31m'
		else:
			return self.getNoColour()
	def getSymbol(self):
		if self.state == "OK": return "="
		elif self.state == "WARN": return "#"
		elif self.state == "ERROR": return "!"

	def occupied(self, current, total):
		return (current*self.width) / total
	def unoccupied(self, current, total):
		return self.width - (current*self.width) / total

	def getNextSpinner(self):
		if self.spinner == '/':
			self.spinner = '-'
		elif self.spinner == '-':
			self.spinner = '\\'
		elif self.spinner == '\\':
			self.spinner = '|'
		elif self.spinner == '|':
			self.spinner = '/'
		return self.spinner		

	def saveCursor(self):
		self.output.write("[s")
	def restoreCursor(self):
		self.output.write("[u")
		self.output.write("[s")
	def cursorDown(self, n):
		self.output.write("[%dB" % n)
	def cursorUp(self, n):
		self.output.write("[%dA" % n)
	def cursorLeft(self, n):
		self.output.write("[%dD" % n)
	def cursorRight(self, n):
		self.output.write("[%dC" % n)
	def clearLine(self):
		self.output.write("[2K")

	def handle(self, record):
		with self.mutex:
			if record.levelno == logging.WARN:
				if self.state == "OK": self.state = "WARN"
			elif record.levelno == logging.ERROR:
				self.state = "ERROR"
			elif record.levelno == logging.CRITICAL and re.match("^\\*\\*\\* *[0-9]*/[0-9]* ", record.getMessage()):
				self.progress = True
				try:
					current = int(re.sub('([0-9]*)/([0-9]*) .*', '\\1', record.getMessage()[3:]))
					total = int(re.sub('([0-9]*)/([0-9]*) .*', '\\2', record.getMessage()[3:]))

					try: 
						line = int(record.threadName[2:])
					except Exception:
						line = 0
					self.cursorDown(line)
					self.cursorLeft(self.fullwidth)
					self.clearLine()
					self.output.write("Progress %s: [%s" % (record.threadName, self.getColour()))
					msg = record.getMessage()
					if len(msg) > self.width: msg=msg[:self.width]
					if len(msg) < self.width: msg=msg+"".join(["-" for x in range(0, self.width-len(msg))])
					cutoff = self.occupied(current, total)
					self.output.write(msg[:cutoff])
					self.output.write(self.getNoColour())
					self.output.write(msg[cutoff:])
					self.output.write(self.getNoColour()+'] (%3d/%3d)' % (current, total))
					if current == total:
						self.progress = False
						self.spinning = False
					self.time = time.time()
				except Exception as e:
					self.output.write("\r%s\n" % e)
				self.cursorUp(line)
				self.output.flush()
			elif record.levelno == logging.CRITICAL and re.match("^\\*\\*\\* XPYBUILD", record.getMessage()):
				self.progress = False
				self.spinning = False
				self.cursorDown(self.workers)
				for l in record.getMessage().split('\n'):
					self.output.write('\r'+l.rstrip())
					for i in range(0, self.width+23-len(l)):
						self.output.write(" ")
					self.output.write('\n')
				self.output.flush()
			elif record.levelno == logging.CRITICAL and re.match("^\\*\\*\\*", record.getMessage()):
				self.spinning = True
				try:
					try: 
						line = int(record.threadName[2:])
					except Exception:
						line = 0
					self.cursorDown(line)
					self.cursorLeft(self.fullwidth)
					self.clearLine()
					msg = record.getMessage()
					if len(msg) > self.width: msg=msg[:self.width]
					if len(msg) < self.width: msg=msg+"".join([" " for x in range(0, self.width-len(msg))])
					self.output.write("Progress %s: [%s]" % (record.threadName, msg))
					self.cursorUp(line)
				except Exception as e:
					self.output.write("\r%s\n" % e)
				self.output.flush()
			else:
				if not self.progress and not self.spinning:
					self.output.write('\r'+record.getMessage().rstrip())
					for i in range(0, self.width+23-len(record.getMessage())):
						self.output.write(" ")
					self.output.write('\n')
					self.output.flush()
				elif 'done in' in record.getMessage():
					try: 
						line = int(record.threadName[2:])
					except Exception:
						line = 0
					self.cursorDown(line)
					self.cursorLeft(self.fullwidth)
					self.clearLine()
					self.output.write("Progress %s: [" % (record.threadName))
					self.cursorUp(line)
					self.output.flush()

if isWindows():
	registerHandler("progress", ProgressBarHandler)
else:
	registerHandler("progress", VT100ProgressBarHandler)


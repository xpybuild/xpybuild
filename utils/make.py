# xpyBuild - eXtensible Python-based Build System
#
# make format logging handler
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
# $Id: make.py 301527 2017-02-06 15:31:43Z matj $
#

# ##teamcity[progressMessage '(%d/%d) %s']

import logging, re, os
from utils.consoleformatter import registerConsoleFormatter, ConsoleFormatter

class MakeConsoleFormatter(ConsoleFormatter):
	"""
	A formatter that logs in a format that matches GNU Make. 

	Required Format:

	file:line: category: description

	"""
	output = None
	def __init__(self, output, buildOptions):
		ConsoleFormatter.__init__(self)
		self.output = output
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
			self.output.write("%s: %s: %s\n" % (location, category, record.getMessage().encode(errors='ignore')))
		else:
			self.output.write("%s\n" % record.getMessage().encode(errors='ignore'))

		self.output.flush()


registerConsoleFormatter("make", MakeConsoleFormatter)

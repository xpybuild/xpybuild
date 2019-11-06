# xpyBuild - eXtensible Python-based Build System
#
# visual studio format logging handler
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
# $Id: visualstudio.py 301527 2017-02-06 15:31:43Z matj $
#

# ##teamcity[progressMessage '(%d/%d) %s']

import logging, re, os
from xpybuild.utils.consoleformatter import registerConsoleFormatter, ConsoleFormatter

class VisualStudioConsoleFormatter(ConsoleFormatter):
	"""
	An alternative log handler than adds some VS-format output messages.

	Required Format::

		<location>: <category> <number>: <description>

	Where:
		- category = warning or error
		- number = specific error or warning number
		- location = <string> or <path>(line) or <path>(line-line) or <path>(line,col) or <path>(line,col-col)
		- description = free-form string

	"""
	output = None
	def __init__(self, output, **kwargs):
		ConsoleFormatter.__init__(self, output, **kwargs)
		self.fmt = logging.Formatter()
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

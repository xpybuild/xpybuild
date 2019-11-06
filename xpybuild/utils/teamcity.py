# xpyBuild - eXtensible Python-based Build System
#
# teamcity format logging handler
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
# $Id: teamcity.py 301527 2017-02-06 15:31:43Z matj $
#

# ##teamcity[progressMessage '(%d/%d) %s']

import logging, re, os

from xpybuild.utils.consoleformatter import registerConsoleFormatter, ConsoleFormatter, publishArtifact

def _publishArtifact(path):
	"""
	@deprecated: Use L{utils.consoleformatter.publishArtifact} instead
	"""
	# legacy implementation for compatibility with xpybuild scripts before 1.12
	publishArtifact('<artifact>', path)

def _teamcityEscape(s):
	# to be on the safe side, remove all non-ascii chars
	s = s.encode('ascii', errors='replace').decode('ascii')
	
	s = s.replace('\r','').strip()
	s = s.replace('|', '||')
	s = s.replace("'", "|'")
	s = s.replace('[', '|[')
	s = s.replace(']', '|]')
	s = s.replace('\n', '|n')
	return s


class TeamcityHandler(ConsoleFormatter):
	"""
	An alternative log handler than adds some teamcity-format output messages.
	"""
	def __init__(self, output, buildOptions, **kwargs):
		ConsoleFormatter.__init__(self, output, buildOptions, **kwargs)
		
		self.bufferingDisabled = True # useful to let teamcity know as soon as there is an error
		
	def handle(self, record):
		if record.getMessage().startswith("##teamcity"):
			self.output.write("%s\n" % record.getMessage())
		elif record.levelno == logging.ERROR:
			self.output.write("##teamcity[message text='%s' status='ERROR']\n" % _teamcityEscape(record.getMessage()))
		elif record.levelno == logging.CRITICAL and record.getMessage().startswith("***"):
			self.output.write("##teamcity[progressMessage '%s']\n" % _teamcityEscape(record.getMessage()))
		else:
			self.output.write("##teamcity[message text='%s']\n" % _teamcityEscape(record.getMessage()))
		self.output.flush()
	
	def publishArtifact(self, logger, displayName, path):
		# displayName is ignored for teamcity
		logger.critical("##teamcity[publishArtifacts '%s']" % _teamcityEscape(path))

	
registerConsoleFormatter("teamcity", TeamcityHandler)

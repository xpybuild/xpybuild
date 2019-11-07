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
import os, logging
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *
from xpybuild.utils.outputhandler import *

from xpybuild.targets.custom import CustomCommand

class MyHandler(ProcessOutputHandler):
	def _decideLogLevel(self, line, isstderr):
		assert isstderr==False
		logging.getLogger('xypbuild').critical('Got: %s', line)
		return logging.ERROR

	def handleEnd(self, returnCode=None):
		logging.getLogger('xypbuild').critical('MyHandler.handleEnd was called')
		assert returnCode==0, 'Unexpected return code'
		raise BuildException('Simulated error from handleEnd: '+', '.join(self._errors))

def encodingDecoder(context, exename, **extra):
	logging.getLogger('xpybuild').critical('Test processOutputEncodingDecider called with exename='+exename)
	return 'ascii'

CustomCommand('${OUTPUT_DIR}/output.txt', [
		os.getenv('ComSpec', 'cmd.exe'), '/c', 'echo Hello world'] if IS_WINDOWS else [
		'/usr/bin/env', 'echo', 'Hello world'], 
	dependencies=[],
	redirectStdOutToTarget=True,
	).option('CustomCommand.outputHandlerFactory', MyHandler).option('common.processOutputEncodingDecider', encodingDecoder)

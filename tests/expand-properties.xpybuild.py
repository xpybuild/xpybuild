#
# Copyright (c) 2013 - 2017 Software AG, Darmstadt, Germany and/or its licensors
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
from propertysupport import *
from buildcommon import *
from pathsets import *

from targets.custom import Custom

definePathProperty('DIR', 'output')
defineStringProperty('NAMES[]', 'ONE, TWO, THREE')
defineStringProperty('SUFFIX', '.jar')
defineStringProperty('ONE', '1')
defineStringProperty('TWO', '2')
defineStringProperty('THREE', '3')
defineStringProperty('EXTRA[]', 'FOUR, ${NAMES[]}')
defineStringProperty('EXTRAS', 'FOUR, ${NAMES[]}')

def echoProperty(value):
	def _echoProperty(target, deps, context):
		logger = logging.getLogger("echoProperty")
		logger.critical("%s =stringexpand= %s", value, context.expandPropertyValues(value))
		logger.critical("%s =listexpand= %s", value, context.expandPropertyValues(value, expandList=True))
		for x in context.expandPropertyValues(value, expandList=True):
			logger.critical("%s =expand= %s", x, context.expandPropertyValues(x))

	return _echoProperty

Custom('test1', [], echoProperty("${DIR}/${SUFFIX}"))
Custom('test2', [], echoProperty("${DIR}/${NAMES[]}${SUFFIX}"))
Custom('test3', [], echoProperty("${NAMES[]}"))
Custom('test4', [], echoProperty("'${NAMES[]}'"))
Custom('test5', [], echoProperty("$${${NAMES[]}}"))
Custom('test6', [], echoProperty("pre/${EXTRAS}/suf"))
Custom('test7', [], echoProperty("pre/${EXTRA[]}/suf"))
Custom('test8', [], echoProperty("${NAMES[]}/${NAMES[]}"))

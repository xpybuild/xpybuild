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
from propertysupport import *
from buildcommon import *
from pathsets import *

from targets.custom import Custom

enableEnvironmentPropertyOverrides(prefix='APB_')

defineStringProperty('PROP', None)

def echoProperty(target, deps, context):
	logger = logging.getLogger("echoProperty")
	logger.critical("Set PROP to the following values and ensure that it's printed out. Also try them setting with APB_PROP in the environment:")
	logger.critical("* 'AB'")
	logger.critical("* 'A B'")
	logger.critical("* 'A=B'")
	logger.critical("* 'A=1 B=2 C=3'")
	logger.critical(context.expandPropertyValues("current value: PROP=${PROP}"))

Custom('dummy', [], echoProperty)

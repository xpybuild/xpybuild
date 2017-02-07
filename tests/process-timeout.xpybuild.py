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

from targets.custom import CustomCommand, Custom
from utils.process import call

setGlobalOption('process.timeout', 2)

CustomCommand('dummy1', ['/bin/cat'], []) # should fail after 2s

Custom('dummy2', [], lambda x, y, z: call(['/bin/cat'], timeout=2)) # should also fail after 2s

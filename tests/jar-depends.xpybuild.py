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
from targets.java import Jar
from utils.process import call

# if you change the returned value in testa.java it shouldn't rebuild testb.java
# and still shouldn't on a subsequent rebuild
Jar('${OUTPUT_DIR}/testa.jar', 'src/testa.java', classpath=None, manifest=None)
Jar('${OUTPUT_DIR}/testb.jar', 'src/testb.java', classpath='${OUTPUT_DIR}/testa.jar', manifest=None)


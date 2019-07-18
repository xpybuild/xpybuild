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
import os
from propertysupport import *
from buildcommon import *
from pathsets import *

from targets.native import *
from targets.copy import Copy
from utils.compilers import GCC, VisualStudio

include(os.environ['PYSYS_TEST_ROOT_DIR']+'/build_utilities/native_config.xpybuild.py')

Copy('${OUTPUT_DIR}/my-generated-include-files/', FindPaths('./include-src/'))
Copy('${OUTPUT_DIR}/my-generated-include-files2/generatedpath/test3.h', FindPaths('./include-src/generatedpath/'))
Copy('${OUTPUT_DIR}/test-generated.cpp', './test.cpp')

Cpp(objectname('${OUTPUT_DIR}/no-target-deps'), './test.cpp',
		includes=[
			"./include/",
			'./include-src/',
		]
)

Cpp(objectname('${OUTPUT_DIR}/target-cpp-and-include-dir'), '${OUTPUT_DIR}/test-generated.cpp',
		includes=[
			"./include/",
			'${OUTPUT_DIR}/my-generated-include-files/', # a target
		]
)

Cpp(objectname('${OUTPUT_DIR}/target-cpp'), '${OUTPUT_DIR}/test-generated.cpp',
		includes=[
			"./include/",
			'./include-src/',
		]
)

Cpp(objectname('${OUTPUT_DIR}/target-include-dir'), './test.cpp',
		includes=[
			"./include/",
			'${OUTPUT_DIR}/my-generated-include-files/', # a target
		]
)

# generated include files in non-target directories are no longer supported

Cpp(objectname('${OUTPUT_DIR}/target-include-file'), './test.cpp',
		includes=[
			"./include/",
			TargetsWithinDir('${OUTPUT_DIR}/my-generated-include-files2/'), # NOT a target, but contains one
		]
)

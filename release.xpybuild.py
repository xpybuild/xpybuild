# Build script for releasing xpybuild itself

#
# Copyright (c) 2013 - 2018 Software AG, Darmstadt, Germany and/or its licensors
# Copyright (c) 2013 - 2019 Ben Spiller and Matthew Johnson
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
# $Id: root.xpybuild.py 301527 2017-02-06 15:31:43Z matj $


# xpybuild release build file. Creates pydoc API docs and versioned zip file for releases.
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.zip import Zip
from xpybuild.targets.copy import Copy
from xpybuild.targets.writefile import WriteFile
from xpybuild.targets.custom import CustomCommand

requireXpyBuildVersion('3.0')

# Need the caller to provide the path to epydoc
#definePathProperty('EPYDOC_ROOT', None, mustExist=True) # parent of the /lib directory; used for local builds but not Travis
defineOutputDirProperty('OUTPUT_DIR', 'release-output')
with open('xpybuild/XPYBUILD_VERSION') as f: defineStringProperty('VERSION', f.read().strip())

Copy('${OUTPUT_DIR}/doc/', FindPaths('doc/', includes='*.md')) # simulate creation of API docs
"""CustomCommand('${OUTPUT_DIR}/doc/api/', 
	command=[ 
		sys.executable, 
		'-m', 'epydoc.cli', 
		'-o', CustomCommand.TARGET, 
		'--no-private', 
		'-v', 
		'--name', 'xpybuild v${VERSION}', 
		'--fail-on-docstring-warning',
		CustomCommand.DEPENDENCIES 
	], 
	dependencies=FindPaths('./', includes='**/*.py', excludes=['**/root.xpybuild.py', 'tests/**', 'internal/**', 'xpybuild.py']),
	env={'PYTHONPATH' : PathSet('${EPYDOC_ROOT}/lib')}
	)
"""
# Zip all the distributables into a release zip file, but not documentation.
Zip('${OUTPUT_DIR}/xpybuild_${VERSION}.zip', [
		AddDestPrefix('xpybuild/',[
			FindPaths('./xpybuild/', includes=['**/*.py']),
			'xpybuild/XPYBUILD_VERSION',
			'LICENSE.txt',
			'README.rst',
			'CHANGELOG.rst',
		]),
		'xpybuild.py',
		])



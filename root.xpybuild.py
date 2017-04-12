# xpyBuild - eXtensible Python-based Build System
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
# $Id: root.xpybuild.py 301527 2017-02-06 15:31:43Z matj $
# Requires: Python 2.7


# xpybuild release build file. Creates pydoc API docs and versioned zip file for releases.

from propertysupport import *
from buildcommon import *
from pathsets import *

from targets.zip import Zip
from targets.copy import Copy
from targets.custom import CustomCommand

from utils.process import call

requireXpyBuildVersion('1.2')

# Need the caller to provide the path to epydoc
definePathProperty('EPYDOC_ROOT', None, mustExist=True) # parent of the /lib directory
defineOutputDirProperty('OUTPUT_DIR', 'release-output')
definePropertiesFromFile('release.properties')

def markdownToTxt(f): return f.replace('.md', '.txt')

CustomCommand('${OUTPUT_DIR}/doc/api/', 
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

# Zip all the distributables into a release zip file.
Zip('${OUTPUT_DIR}/xpybuild_${VERSION}.zip', [
		AddDestPrefix('doc/api/', FindPaths(DirGeneratedByTarget('${OUTPUT_DIR}/doc/api/'))),
		AddDestPrefix('doc/', MapDest(markdownToTxt, FindPaths('doc/', includes=['*.md']))),
		FindPaths('./', includes='**/*.py', excludes='tests/**'),
		'release.properties',
		MapDest(markdownToTxt, 'README.md'),
		'LICENSE.txt',
		])



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

from xpybuild.targets.archive import Zip
from xpybuild.targets.copy import Copy
from xpybuild.targets.writefile import WriteFile
from xpybuild.targets.custom import CustomCommand
from xpybuild.utils.outputhandler import ProcessOutputHandler

requireXpyBuildVersion('3.0')

try:
	import sphinx
except ImportError:
	raise Exception('Cannot build the xpybuild release as sphinx documentation library is not installed into this Python installation: %s (see .travis.yml for details of how to install)'%sys.executable)

defineOutputDirProperty('OUTPUT_DIR', '_build_output')
with open('xpybuild/XPYBUILD_VERSION') as f: defineStringProperty('VERSION', f.read().strip())

CustomCommand('${OUTPUT_DIR}/docs/', 
	command=[ 
		sys.executable,
		'-m', 'sphinx',
		'-M', 'html',
		PathSet('./docs/'), # source dir
		'${OUTPUT_DIR}/docs/', # output dir
	], 
	dependencies=[
		FindPaths('docs/', excludes=['autodocgen/**']),
		FindPaths('./xpybuild/', includes=['**/*.py']),
		'xpybuild/XPYBUILD_VERSION',
		'CHANGELOG.rst',
	],
	stderr='${OUTPUT_DIR}/doc_warnings.txt',
	).tags('docs'
	).option( 
		# ProcessOutputHandler converts stderr lines from sphinx into target ERRORs
		'CustomCommand.outputHandlerFactory', ProcessOutputHandler
	).option(
		# workaround for https://github.com/readthedocs/sphinx_rtd_theme/issues/739
		'ProcessOutputHandler.regexIgnore', '.*(RemovedInSphinx30Warning| [{][{] super[(][)] [}][}]).*'
	)

Zip('${OUTPUT_DIR}/xpybuild_${VERSION}_docs.zip', [
		FindPaths(DirGeneratedByTarget('${OUTPUT_DIR}/docs/')+'html/'),
		'LICENSE.txt',
		'README.rst',
])

# Zip all the distributables into a release zip files
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



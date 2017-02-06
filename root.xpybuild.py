# xpyBuild - eXtensible Python-based Build System
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
# $Id: root.xpybuild.py 301527 2017-02-06 15:31:43Z matj $
# Requires: Python 2.7


# xpybuild release build file. Creates pydoc API docs, changelog and versionned zip file for releases.

from propertysupport import *
from buildcommon import *
from pathsets import *

from targets.zip import Zip
from targets.custom import Custom

from utils.process import call
from utils.fileutils import openForWrite
from utils.outputhandler import ProcessOutputHandler

import xml.etree.ElementTree as ET

requireXpyBuildVersion('1.2')

# Need the caller to provide the path to epydoc
definePathProperty('EPYDOC_ROOT', None, mustExist=True) # points to the /lib directory
defineOutputDirProperty('OUTPUT_DIR', 'release')
definePropertiesFromFile('release.properties')

# Custom function to call epydoc to create the release API docs
def createdoc(path, deps, context):
	log = logging.getLogger('pydoc')
	command = [ sys.executable, '-m', 'epydoc.cli', '-o', path, '--no-private' ]
	command.extend(deps)
	environs = { 'PYTHONPATH' : context.expandPropertyValues('${EPYDOC_ROOT}') }
	call(command, env=environs, timeout=context.mergeOptions()['process.timeout'])

Custom('${OUTPUT_DIR}/doc/', FindPaths('./', includes='**/*.py', excludes='**/root.xpybuild.py'), createdoc)


# Zip all the distributables into a release zip file.
Zip('${OUTPUT_DIR}/xpybuild_${VERSION}.zip', [
		AddDestPrefix('api-doc/', FindPaths(DirGeneratedByTarget('${OUTPUT_DIR}/doc/'))),
		FindPaths('./', includes='**/*.py'),
		'using-xpybuild.pdf',
		'release.properties',
		'README.txt',
		])



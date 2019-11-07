from xpybuild.buildcommon import enableLegacyXpybuildModuleNames
enableLegacyXpybuildModuleNames()

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

from targets.docker import DockerBuild, DockerPushTag

definePathProperty('DOCKER_PATH', None)
defineStringProperty('DOCKER_HOST', None)
defineStringProperty('DOCKER_REPO', None)
defineStringProperty('DOCKER_USER', None)
setGlobalOption('docker.path', '${DOCKER_PATH}/docker')
setGlobalOption('docker.host', '${DOCKER_HOST}')

DockerBuild('testbase:latest', ['./'])
#DockerPushTag('${DOCKER_REPO}/${DOCKER_USER}/testbase:latest', 'testbase:latest')

from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.writefile import *
from xpybuild.targets.copy import *

defineOutputDirProperty('OUTPUT_DIR', None)

definePathProperty('DOCKER_EXE', None)
from xpybuild.targets.docker import *
setGlobalOption('docker.path', '${DOCKER_EXE}')
setGlobalOption('docker.host', 'ssh://localhost:0')

DockerBase('xpybuild_non_existent_image_name', [])
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.archive import *

defineOutputDirProperty('OUTPUT_DIR', None)
definePathProperty('INPUT_DIR', None)

Unpack('${OUTPUT_DIR}/unpacked/', '${INPUT_DIR}/myarchive.tar.xz')


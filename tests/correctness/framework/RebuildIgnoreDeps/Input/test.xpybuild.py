from xpybuild.buildcommon import enableLegacyXpybuildModuleNames

import os, logging, time
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

defineOutputDirProperty('OUTPUT_DIR', None)

from xpybuild.targets.writefile import *
from xpybuild.targets.copy import *

WriteFile('${OUTPUT_DIR}/writefile.txt', 'Hello')

Copy('${OUTPUT_DIR}/copyfile.txt', '${OUTPUT_DIR}/writefile.txt').tags('mycopy')

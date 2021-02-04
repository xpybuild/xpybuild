import os, logging, time, random
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

defineOutputDirProperty('OUTPUT_DIR', None)

from xpybuild.targets.writefile import *
from xpybuild.targets.copy import *

defineStringProperty('RANDOM', str(random.random()))
WriteFile('${OUTPUT_DIR}/writefile-${RANDOM}.txt', 'Hello')

Copy('${OUTPUT_DIR}/copyfile.txt', '${OUTPUT_DIR}/writefile-${RANDOM}.txt').tags('mycopy')

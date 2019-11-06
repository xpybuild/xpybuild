import os, logging
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *


defineOutputDirProperty('OUTPUT_DIR', None)

from xpybuild.targets.copy import Copy

for i in range(0, 3500):
	Copy('${OUTPUT_DIR}/output%s/'%i, FindPaths('${OUTPUT_DIR}/../input-files/', includes='**/*.txt'))

import os, logging
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *


defineOutputDirProperty('OUTPUT_DIR', None)

defineStringProperty('NUMBER_TARGETS', '1')
defineStringProperty('NUMBER_PATTERNS', '50')
defineStringProperty('PATTERN', '')

includes = [getPropertyValue('PATTERN')]
if not includes[0]: includes = [("included/test%d.*"%i) for i in range(int(getPropertyValue('NUMBER_PATTERNS')))]

from xpybuild.targets.copy import Copy

for i in range(0, int(getPropertyValue('NUMBER_TARGETS'))):
	Copy('${OUTPUT_DIR}/copy%d/'%i, [FindPaths('${OUTPUT_DIR}/../findpathsroot/', 
		# match specific filenames from included directory, nothing from excluded
		includes=includes
		)])
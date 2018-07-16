import os, logging
from propertysupport import *
from buildcommon import *
from pathsets import *


defineOutputDirProperty('OUTPUT_DIR', None)

defineStringProperty('NUMBER_TARGETS', '1')
defineStringProperty('NUMBER_PATTERNS', '50')


from targets.copy import Copy

for i in range(0, int(getPropertyValue('NUMBER_TARGETS'))):
	Copy('${OUTPUT_DIR}/copy%d/'%i, [FindPaths('${OUTPUT_DIR}/../findpathsroot/', 
		# match specific filenames from included directory, nothing from excluded
		includes=['included/test%d.*'%i for i in range(int(getPropertyValue('NUMBER_PATTERNS')))]
		)])
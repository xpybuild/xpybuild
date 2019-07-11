import os, logging
from propertysupport import *
from buildcommon import *
from pathsets import *


defineOutputDirProperty('OUTPUT_DIR', None)

# these are not used explciitly here, but must be checked to ensure inputs aren't generatred by targets
defineOutputDirProperty('OUTPUT_DIR2', './OUTPUT_DIR2/')
defineOutputDirProperty('OUTPUT_DIR2_NESTED', './OUTPUT_DIR2/nested/')

from targets.copy import Copy

for i in range(0, 3500):
	Copy('${OUTPUT_DIR}/output%s/'%i, 
		['${OUTPUT_DIR}/../input-files/input-%d.txt'%x for x in range(0, 256+1)])

import os, logging
from propertysupport import *
from buildcommon import *
from pathsets import *


defineOutputDirProperty('OUTPUT_DIR', None)

from targets.copy import Copy

for i in range(0, 3500):
	Copy('${OUTPUT_DIR}/output%s/'%i, 
		['${OUTPUT_DIR}/../input-files/input-%d.txt'%x for x in range(0, 256+1)])

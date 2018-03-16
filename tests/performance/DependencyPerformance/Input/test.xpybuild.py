import os, logging
from propertysupport import *
from buildcommon import *
from pathsets import *


defineOutputDirProperty('OUTPUT_DIR', None)

from targets.copy import Copy

for i in range(0, 256):
	Copy('${OUTPUT_DIR}/outputa-%s/'%i, ["input-%s.txt"%x for x in range(0, 256)])
	Copy('${OUTPUT_DIR}/outputb-%s/'%i, FindPaths(DirGeneratedByTarget("${OUTPUT_DIR}/outputa-%s/"%i)))
	Copy('${OUTPUT_DIR}/outputc-%s/'%i, FindPaths(DirGeneratedByTarget("${OUTPUT_DIR}/outputb-%s/"%i)))
	Copy('${OUTPUT_DIR}/outputd-%s/'%i, FindPaths(DirGeneratedByTarget("${OUTPUT_DIR}/outputc-%s/"%i)))
	Copy('${OUTPUT_DIR}/outpute-%s/'%i, FindPaths(DirGeneratedByTarget("${OUTPUT_DIR}/outputd-%s/"%i)))
	Copy('${OUTPUT_DIR}/outputf-%s/'%i, FindPaths(DirGeneratedByTarget("${OUTPUT_DIR}/outpute-%s/"%i)))
	for j in range(1, 10):
		if i > j:
			Copy('${OUTPUT_DIR}/outputa-%s-%s/'%(i, j), FindPaths(DirGeneratedByTarget("${OUTPUT_DIR}/outputa-%s/"%(i-j))))

import os, logging
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *
from xpybuild.targets.copy import Copy
from xpybuild.targets.writefile import WriteFile

defineOutputDirProperty('OUTPUT_DIR', None)

WriteFile('${OUTPUT_DIR}/dir1/foo1.txt', 'Hello world 1')
WriteFile('${OUTPUT_DIR}/dir1/dirA/dirB/foo2.txt', 'Hello world 2')
WriteFile('${OUTPUT_DIR}/dir2/dirC/foo3.txt', 'Hello world 3')

Copy('${OUTPUT_DIR}/CopyFromTargetsWithinDir-FindPaths/', FindPaths(TargetsWithinDir('${OUTPUT_DIR}/dir1/')))
Copy('${OUTPUT_DIR}/CopyFromTargetsWithinDir/', (TargetsWithinDir('${OUTPUT_DIR}/dir1/')))

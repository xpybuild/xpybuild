import os, logging
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *
from xpybuild.targets.copy import Copy

defineOutputDirProperty('OUTPUT_DIR', None)

Copy('${OUTPUT_DIR}/findpaths-out/', FindPaths('${OUTPUT_DIR}/../findpaths/', includes=['**/', '**']))
Copy('${OUTPUT_DIR}/dirbased-out/', DirBasedPathSet('${OUTPUT_DIR}/../dirbased/', 'a', 'b'))


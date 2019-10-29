import os, logging
from propertysupport import *
from buildcommon import *
from pathsets import *
from targets.copy import Copy

defineOutputDirProperty('OUTPUT_DIR', None)

Copy('${OUTPUT_DIR}/findpaths-out/', FindPaths('${OUTPUT_DIR}/../findpaths/', includes=['**/', '**']))
Copy('${OUTPUT_DIR}/dirbased-out/', DirBasedPathSet('${OUTPUT_DIR}/../dirbased/', 'a', 'b'))


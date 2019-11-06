from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.copy import *

defineOutputDirProperty('OUTPUT_DIR', None)

Copy('${OUTPUT_DIR}/testtarget1', 'input.txt')
Copy('${OUTPUT_DIR}/testtarget2/', ['${OUTPUT_DIR}/testtarget2a', '${OUTPUT_DIR}/testtarget2b'])

Copy('${OUTPUT_DIR}/testtarget2a-dep', 'input.txt')

Copy('${OUTPUT_DIR}/testtarget2a', '${OUTPUT_DIR}/testtarget2a-dep')
Copy('${OUTPUT_DIR}/testtarget2b', 'input.txt')
Copy('${OUTPUT_DIR}/testtarget3/', ['${OUTPUT_DIR}/testtarget2a', '${OUTPUT_DIR}/testtarget2b'])
Copy('${OUTPUT_DIR}/testtarget4/', ['${OUTPUT_DIR}/testtarget2a', '${OUTPUT_DIR}/testtarget2b'])
Copy('${OUTPUT_DIR}/testtarget5', 'input.txt')
Copy('${OUTPUT_DIR}/testtarget6', 'input.txt')

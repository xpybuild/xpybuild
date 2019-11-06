from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.copy import *

defineOutputDirProperty('OUTPUT_DIR', None)

Copy('${OUTPUT_DIR}/testtarget1', 'input.txt')
Copy('${OUTPUT_DIR}/testtarget2/', ['${OUTPUT_DIR}/testtarget2a', '${OUTPUT_DIR}/testtarget2b']).priority(15.1) 
#Copy('${OUTPUT_DIR}/testtarget1a/', ['${OUTPUT_DIR}/testtarget2a', '${OUTPUT_DIR}/testtarget2b']).priority(100) 

Copy('${OUTPUT_DIR}/testtarget2a-dep', 'input.txt').priority(10.1)

Copy('${OUTPUT_DIR}/testtarget2a', '${OUTPUT_DIR}/testtarget2a-dep')
Copy('${OUTPUT_DIR}/testtarget2b', 'input.txt').priority(20.2)
Copy('${OUTPUT_DIR}/testtarget3/', ['${OUTPUT_DIR}/testtarget2a', '${OUTPUT_DIR}/testtarget2b']).priority(16.1) # should affect the priority of dependency 2a
Copy('${OUTPUT_DIR}/testtarget4/', ['${OUTPUT_DIR}/testtarget2a', '${OUTPUT_DIR}/testtarget2b']).priority(0.5)
Copy('${OUTPUT_DIR}/testtarget5', 'input.txt').priority(1) # an integer
Copy('${OUTPUT_DIR}/testtarget6', 'input.txt')

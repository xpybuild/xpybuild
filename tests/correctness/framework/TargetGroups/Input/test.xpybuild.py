from propertysupport import *
from buildcommon import *
from pathsets import *

from targets.copy import *

defineOutputDirProperty('OUTPUT_DIR', None)

defineAtomicTargetGroup([
	Copy('${OUTPUT_DIR}/testtarget1', 'input.txt'),
	Copy('${OUTPUT_DIR}/testtarget2', 'input.txt'),
])
Copy('${OUTPUT_DIR}/testtarget3', 'input.txt')

Copy('${OUTPUT_DIR}/testtarget4', '${OUTPUT_DIR}/testtarget1')

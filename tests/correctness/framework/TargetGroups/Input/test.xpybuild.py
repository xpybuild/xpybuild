from propertysupport import *
from buildcommon import *
from pathsets import *

from targets.copy import *

defineOutputDirProperty('OUTPUT_DIR', None)

defineAtomicTargetGroup([
	Copy('${OUTPUT_DIR}/testtarget1a', 'input.txt'),
	Copy('${OUTPUT_DIR}/testtarget1b', 'input.txt'),
])

defineAtomicTargetGroup([
	Copy('${OUTPUT_DIR}/testtarget2a', 'input.txt'),
	Copy('${OUTPUT_DIR}/testtarget2b', 'input.txt'),
])

defineAtomicTargetGroup([
	Copy('${OUTPUT_DIR}/testtarget-not-in-group', 'input.txt')
])

Copy('${OUTPUT_DIR}/testtarget/', 
	['${OUTPUT_DIR}/testtarget1a', 
	'${OUTPUT_DIR}/testtarget2a',
	'${OUTPUT_DIR}/testtarget2b',# explicit dep as well as target group dep
	]
	)

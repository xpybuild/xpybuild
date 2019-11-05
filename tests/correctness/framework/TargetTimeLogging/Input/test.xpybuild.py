from propertysupport import *
from buildcommon import *
from pathsets import *

from targets.copy import *
from build_utilities.sleep import Sleep

defineOutputDirProperty('OUTPUT_DIR', None)

Copy('${OUTPUT_DIR}/testtarget1', 'input.txt')
Copy('${OUTPUT_DIR}/testtarget2/', ['${OUTPUT_DIR}/testtarget2a', '${OUTPUT_DIR}/testtarget2b'])

Copy('${OUTPUT_DIR}/testtarget2a-dep', 'input.txt')

Copy('${OUTPUT_DIR}/testtarget2a', '${OUTPUT_DIR}/testtarget2a-dep')
Copy('${OUTPUT_DIR}/testtarget2b', 'input.txt')
Copy('${OUTPUT_DIR}/testtarget3/', ['${OUTPUT_DIR}/testtarget2a', '${OUTPUT_DIR}/testtarget2b'])
Copy('${OUTPUT_DIR}/testtarget4/', ['${OUTPUT_DIR}/testtarget2a', '${OUTPUT_DIR}/testtarget2b'])
Copy('${OUTPUT_DIR}/test,target5', 'input.txt')
Copy('${OUTPUT_DIR}/testtarget6', 'input.txt')

# encode this graph:
# {A,B} - C - {D, E, F} - G
#              |- H  - I - J
#
# critical path should be [A|B]-C-D-H-I-J
# For J critical path time should be ~6N
#
# For G crit time should be ~4N
#       cum time should be ~7N
#       time should be N
N = 1.39728

Sleep('${OUTPUT_DIR}/sleepA', N)
Sleep('${OUTPUT_DIR}/sleepB', N)
Sleep('${OUTPUT_DIR}/sleepC', N, ['${OUTPUT_DIR}/sleepA', '${OUTPUT_DIR}/sleepB'])
Sleep('${OUTPUT_DIR}/sleepD', N, ['${OUTPUT_DIR}/sleepC'])
Sleep('${OUTPUT_DIR}/sleepE', N, ['${OUTPUT_DIR}/sleepC'])
Sleep('${OUTPUT_DIR}/sleepF', N, ['${OUTPUT_DIR}/sleepC'])
Sleep('${OUTPUT_DIR}/sleepG', N, ['${OUTPUT_DIR}/sleepD', '${OUTPUT_DIR}/sleepE', '${OUTPUT_DIR}/sleepF'])
Sleep('${OUTPUT_DIR}/sleepH', N, ['${OUTPUT_DIR}/sleepD'])
Sleep('${OUTPUT_DIR}/sleepI', N, ['${OUTPUT_DIR}/sleepH'])
Sleep('${OUTPUT_DIR}/sleepJ', N, ['${OUTPUT_DIR}/sleepI'])


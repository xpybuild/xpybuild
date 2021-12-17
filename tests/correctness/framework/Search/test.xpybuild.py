from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.writefile import *
from xpybuild.targets.copy import *

defineOutputDirProperty('OUTPUT_DIR', None)

defineStringProperty('DOT', '.')

defineStringProperty('PROP1', 'prop value1')
defineStringProperty('PROP2', 'prop value2')

defineOption('MyOption1', 'opt1')
defineOption('MyOption2', 'opt2')

WriteFile('${OUTPUT_DIR}/target1${DOT}txt', 'Hi').tags('mytag1')
WriteFile('${OUTPUT_DIR}/target2.txt', 'Hi').tags('mytag2')

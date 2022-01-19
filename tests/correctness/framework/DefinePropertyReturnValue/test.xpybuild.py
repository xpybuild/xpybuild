from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.writefile import *
from xpybuild.targets.copy import *

defineOutputDirProperty('OUTPUT_DIR', None)

assert defineStringProperty('MY_PROP', 'abc')
assert defineStringProperty('STR_PROP', '${MY_PROP}def') == 'abcdef'

assert os.path.exists(definePathProperty('PATH_PROP', '${OUTPUT_DIR}/..'))

WriteFile('${OUTPUT_DIR}/output.txt', 'noop')


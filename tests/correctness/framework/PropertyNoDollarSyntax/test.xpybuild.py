from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.writefile import *
from xpybuild.targets.copy import *

defineOutputDirProperty('OUTPUT_DIR', None)

defineStringProperty('PROP_FOO', 'foo')
defineStringProperty('PROP_BAR', 'bar')
defineStringProperty('PROP_BOTH', '${PROP_FOO}{PROP_BAR}')

defineOption('myOption', '${PROP_FOO}{PROP_BAR}')

WriteFile('${OUTPUT_DIR}/output-${PROP_FOO}{PROP_BAR}.txt', 'Hello')

WriteFile('${OUTPUT_DIR}/escaping1-$${literal1}.txt', 'Hello')
WriteFile('${OUTPUT_DIR}/escaping2-{{}literal2}.txt', 'Hello')



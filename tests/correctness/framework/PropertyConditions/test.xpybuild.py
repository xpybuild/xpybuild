from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.writefile import *
from xpybuild.targets.copy import *

defineOutputDirProperty('OUTPUT_DIR', None)

definePropertiesFromFile('test.properties', conditions=['c2', 'c3'])

WriteFile('${OUTPUT_DIR}/props.txt', '\n'.join([
	'${MY_PROPERTY_A}',
	'${MY_PROPERTY_B}',
	'${MY_PROPERTY_C}',
	'${MY_PROPERTY_D}',
]))


from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.writefile import *
from xpybuild.targets.copy import *
from xpybuild.utils.fileutils import *

defineOutputDirProperty('OUTPUT_DIR', None)


d = parsePropertiesFile(definePathProperty('PROPS_FILE', None), asDict=True)
WriteFile('${OUTPUT_DIR}/props.txt', '\n'.join(['foo='+d['foo'], 'baz='+d['baz']]))

from xpybuild.propertysupport import enableLegacyXpybuildModuleNames
enableLegacyXpybuildModuleNames()

from propertysupport import *
from buildcommon import *
from pathsets import *

from targets.copy import *

defineOutputDirProperty('OUTPUT_DIR', None)

FilteredCopy('${OUTPUT_DIR}/unused-mapper.txt', 'input.txt', StringReplaceLineMapper('x', 'X'))

from xpybuild.buildcommon import enableLegacyXpybuildModuleNames
enableLegacyXpybuildModuleNames()

from propertysupport import *
from buildcommon import *
from pathsets import *

from targets.copy import *

defineOutputDirProperty('OUTPUT_DIR', None)

FilteredCopy('${OUTPUT_DIR}/working-mapper.txt', 'input.txt', StringReplaceLineMapper('aa', 'AA'))

FilteredCopy('${OUTPUT_DIR}/no-mappers.txt', 'input.txt')
FilteredCopy('${OUTPUT_DIR}/empty-mappers.txt', 'input.txt', None, None)
FilteredCopy('${OUTPUT_DIR}/unused-mapper.txt', 'input.txt', StringReplaceLineMapper('x', 'X'), allowUnusedMappers=True)

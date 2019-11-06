from xpybuild.propertysupport import enableLegacyXpybuildModuleNames
enableLegacyXpybuildModuleNames()

from propertysupport import *
from buildcommon import *
from pathsets import *

from targets.copy import *

defineOutputDirProperty('OUTPUT_DIR', None)
defineStringProperty('PROP', '<propval>')

FilteredCopy('${OUTPUT_DIR}/output-default.txt', 'input.txt', StringReplaceLineMapper('a${PROP}a', 'A${PROP}A'))
FilteredCopy('${OUTPUT_DIR}/output-no-expansion.txt', 'input.txt', StringReplaceLineMapper('a${PROP}a${', 'A${PROP}A${', disablePropertyExpansion=True))

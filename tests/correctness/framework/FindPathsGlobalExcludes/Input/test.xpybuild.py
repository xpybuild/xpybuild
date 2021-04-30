from xpybuild.buildcommon import enableLegacyXpybuildModuleNames
enableLegacyXpybuildModuleNames()

import os, logging
from propertysupport import *
from buildcommon import *
from pathsets import *
from targets.copy import Copy

defineOutputDirProperty('OUTPUT_DIR', None)
defineBooleanProperty('CUSTOM_GLOBAL_EXCLUDES', False)
if getPropertyValue('CUSTOM_GLOBAL_EXCLUDES'):
	def customExcludesFunction(name): 
		assert name, name
		assert '\\' not in name, name
		assert '/' not in name.rstrip('/'), name
		return name in ['exclude-file', 'exclude-dir']
		
	setGlobalOption('FindPaths.globalExcludesFunction', customExcludesFunction)

Copy('${OUTPUT_DIR}/CopyOutput/', FindPaths('${OUTPUT_DIR}/../input/', includes=['**', '**/']))


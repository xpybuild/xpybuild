from xpybuild.propertysupport import enableLegacyXpybuildModuleNames
enableLegacyXpybuildModuleNames()

import os, logging, time
from propertysupport import *
from buildcommon import *
from pathsets import *

defineOutputDirProperty('OUTPUT_DIR', None)

from targets.writefile import *
from targets.copy import *

WriteFile('${OUTPUT_DIR}/src-file.txt', 'Hello')

WriteFile('${OUTPUT_DIR}/bar.txt', 'Hello')
Copy('${OUTPUT_DIR}/src-dir/', '${OUTPUT_DIR}/bar.txt')

class CustomCopyTarget(Copy):
		
	def run(self, context):
		r = super(CustomCopyTarget, self).run(context)
		# now be naughty
		
		if self.name.endswith('modified-file.txt'):
			time.sleep(3) # to avoid file system inaccuracies
			open(context.expandPropertyValues('${OUTPUT_DIR}/src-file.txt'), 'w').close()
		else:
			os.remove(context.expandPropertyValues('${OUTPUT_DIR}/src-dir/bar.txt'))
		
		return r

CustomCopyTarget('${OUTPUT_DIR}/deleted-file.txt', FindPaths(DirGeneratedByTarget('${OUTPUT_DIR}/src-dir/')))
CustomCopyTarget('${OUTPUT_DIR}/modified-file.txt', '${OUTPUT_DIR}/src-file.txt')

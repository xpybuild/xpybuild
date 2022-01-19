from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.writefile import *
from xpybuild.targets.copy import *

defineOutputDirProperty('OUTPUT_DIR', None)

WriteFile('${OUTPUT_DIR}/output.txt', '\n'.join(['Hello']))

class CustomTarget(WriteFile):
	def run(self, context):
		self.log.critical('Test message from build file at CRIT level')
		return super(CustomTarget, self).run(context)

CustomTarget('${OUTPUT_DIR}/output.txt', 'Test message')

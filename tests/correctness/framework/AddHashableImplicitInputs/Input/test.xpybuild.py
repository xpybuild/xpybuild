from xpybuild.propertysupport import enableLegacyXpybuildModuleNames
enableLegacyXpybuildModuleNames()

import os, logging
from propertysupport import *
from buildcommon import *
from pathsets import *

defineOutputDirProperty('OUTPUT_DIR', None)

defineStringProperty('MY_PROP1', 'val1')
defineStringProperty('MY_PROP2', 'val2')
defineStringProperty('MY_PROP3', 'val3')
defineOption('myoption', 'val2')


from targets.writefile import *

class CustomTarget(WriteFile):
	def __init__(self, *args, **kwargs):
		super(CustomTarget, self).__init__(*args, **kwargs)
		self.addHashableImplicitInput('addHashableImplicitInput-string=${MY_PROP1}')
		self.addHashableImplicitInput(lambda ctx: ctx.expandPropertyValues('addHashableImplicitInput-callable=${MY_PROP2}'))
		self.addHashableImplicitInputOption('myoption')
		self.addHashableImplicitInput('') # blank line is handy
		
	def run(self, context):
		self.log.warn('Rebuilding test CustomTarget')
		return super(CustomTarget, self).run(context)

CustomTarget('${OUTPUT_DIR}/output.txt', 'Test message').option('myoption', '${MY_PROP3}')

from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.writefile import *
from xpybuild.targets.copy import *

defineOutputDirProperty('OUTPUT_DIR', None)

WriteFile('${OUTPUT_DIR}/writefile-target.txt', '\n'.join(['Hello']))

def demoPostProcessor(context):
	for target in context.targets().values():
		if isinstance(target, MyCustomTarget) or 'FooBar' in target.name: 
			# Override options for these targets
			target.option(BaseTarget.Options.failureRetries, 2)
			
			# Add additional tags for these targets
			target.tags('my-post-processed-tag')
			
			target.disableInFullBuild()

registerBuildLoadPostProcessor(demoPostProcessor)

class MyCustomTarget(WriteFile):
	pass

MyCustomTarget('${OUTPUT_DIR}/custom-target.txt', 'Test message').tags('original-tag')

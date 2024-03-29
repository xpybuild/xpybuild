import os, logging, time
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *
from xpybuild.basetarget import *

defineOutputDirProperty('OUTPUT_DIR', None)

from xpybuild.targets.writefile import *
from xpybuild.targets.copy import *
from xpybuild.utils.fileutils import mkdir

class MyTarget(BaseTarget):
		
	def run(self, context):
		mkdir(self.path)
		if os.listdir(self.path):
			self.log.error('TEST FAILED - clean did not occur between retries')
		
		open(self.path+'/touchfile.txt', 'w').close()
		
		self.log.error('Error logged by target')
		raise Exception('Simulated target failure')
	
	def clean(self, context):
		BaseTarget.clean(self, context)
		logging.getLogger('foo').error('This is an error logged during clean')
		logging.getLogger('foo').warning('This is a warning logged during clean')


# Use a string since that's what it would be if set by a property
MyTarget('${OUTPUT_DIR}/mytarget/', []).option(BaseTarget.Options.failureRetries, '2')

setGlobalOption('Target.failureRetriesInitialBackoffSecs', 1.0)
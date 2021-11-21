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
		
		raise Exception('Simulated target failure')

MyTarget('${OUTPUT_DIR}/mytarget/', []).option(BaseTarget.Options.failureRetries, 2)
setGlobalOption('Target.failureRetriesInitialBackoffSecs', 1.0)
__pysys_title__   = r""" CustomCommand - Message when command fails""" 
#                        ================================================================================

__pysys_purpose__ = r""" 
	
	""" 
	
__pysys_authors__ = "bsp"
__pysys_created__ = "2022-01-06"

import pysys
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):
	def execute(self):
		self.xpybuild(stdouterr='build', args=[], shouldFail=True)

	def validate(self):
		self.assertGrep('build.log', 'full command line is: .*"echo Oh dear') # appropriate (but different) shell escaping on both windows and unix

		self.assertGrep('build.log', 'Target FAILED: <CustomCommand> .*cmd-output/ : .* command #2 failed with error code [0-9]+; see output at ".*._OUTPUT_DIR_.cmd-output.2.out" or look under .*cmd-output')

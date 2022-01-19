__pysys_title__   = r""" CustomCommand - Multiple commands""" 
#                        ================================================================================

__pysys_purpose__ = r"""
	""" 
	
__pysys_authors__ = "bsp"
__pysys_created__ = "2022-01-06"

#__pysys_skipped_reason__   = "Skipped until Bug-1234 is fixed"

import pysys
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):
	def execute(self):
		self.xpybuild(stdouterr='build', args=[])

	def validate(self):
	
		self.assertGrep('build-output/cmd-output/output.txt', 'Hello')
		self.assertGrep('build-output/cmd-output/output.txt', 'world')

		self.assertGrep('build-output/BUILD_WORK/CustomCommandOutput/%s._OUTPUT_DIR_.cmd-output.4.out'%
			('cmd.exe' if IS_WINDOWS else 'bash'), 'All done now!')

		self.assertLineCount('build.log', 'environment overrides for', condition='==1') # should not be repeated for each command
		self.assertGrep('build.log', 'Building .*cmd-output/ by executing command #1:')
		self.assertGrep('build.log', 'Building .*cmd-output/ by executing command #2:')
		self.assertGrep('build.log', 'Building .*cmd-output/ by executing command #3:')
		self.assertGrep('build.log', 'Building .*cmd-output/ by executing command #4:')

		self.assertGrep('build.log', 'output from .*cmd-output/ #1 will be written to.*_OUTPUT_DIR_.cmd-output.err')
		self.assertGrep('build.log', 'output from .*cmd-output/ #2 will be written to.*_OUTPUT_DIR_.cmd-output.2.err')

		self.assertGrep('build.log', 'stdout from .*cmd-output/ #3 is: ')
		self.assertGrep('build.log', 'Stdout rocks')

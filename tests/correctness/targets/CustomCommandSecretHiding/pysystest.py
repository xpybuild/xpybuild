__pysys_title__   = r""" CustomCommand - Hiding of secrets""" 
#                        ================================================================================

__pysys_purpose__ = r"""
	""" 
	
__pysys_authors__ = "bsp"
__pysys_created__ = "2023-06-27"

#__pysys_skipped_reason__   = "Skipped until Bug-1234 is fixed"

import pysys
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):
	def execute(self):
		self.xpybuild(stdouterr='build', args=['INPUT_DIR='+self.input], env={
			'XPYTEST_MY_CUSTOM_PWD_ENV':'my-env-pwd',
			'XPYTEST_MY_CUSTOM_PWD_EMPTY_ENV':'',
			})

	def validate(self):

		self.assertGrep('build-output/cmd-output.txt', 'Command completed successfully')
		self.assertGrep('build.log', '.*hiddentext.*', contains=False)
		self.assertGrep('build.log', 'Setting property MY_PROPERTY_THAT_CONTAINS_A_PWD=prefix-<secret>')
		self.assertGrep('build-output/BUILD_WORK/targets/CustomCommand/implicit-inputs/_OUTPUT_DIR_.cmd-output.txt.txt', '.*hiddentext.*', contains=False)
		self.assertGrep('build-output/BUILD_WORK/targets/CustomCommand/implicit-inputs/_OUTPUT_DIR_.cmd-output.txt.txt', 'hash before secret stripping=8f4721680d2e24688848e1958c1bde63')

		self.assertGrepOfGrep('build.out', 'Overriding property value from environment: MY_CUSTOM_PWD_ENV=(.*)$', expectedRegex='<secret>')
		self.assertGrepOfGrep('build.out', 'Overriding property value from environment: MY_CUSTOM_PWD_EMPTY_ENV=(.*)$', expectedRegex='') # no obfuscation needed if empty
		self.assertGrep('build.log', 'my-env-pwd', contains=False)


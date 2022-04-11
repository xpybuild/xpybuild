__pysys_title__   = r""" Unpack archive - tar.xz """ 
#                        ================================================================================
__pysys_purpose__ = r""" """ 
	
__pysys_authors__ = "bsp"
__pysys_created__ = "2022-03-18"
#__pysys_skipped_reason__   = "Skipped until Bug-1234 is fixed"

import pysys
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):
	def execute(self):
		self.xpybuild(stdouterr='mytest', args=['INPUT_DIR='+self.input])

	def validate(self):
		self.assertGrep('build-output/unpacked/mydir/Hi.txt', expr=r"Hello world")
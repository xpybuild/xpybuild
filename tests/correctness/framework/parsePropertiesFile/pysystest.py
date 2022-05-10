__pysys_title__   = r""" fileutils - parsePropertiesFile""" 
#                        ================================================================================
__pysys_purpose__ = r""" """ 
	
__pysys_authors__ = "bsp"
__pysys_created__ = "2022-05-10"
#__pysys_skipped_reason__   = "Skipped until Bug-1234 is fixed"

import pysys
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):
	def execute(self):
		self.xpybuild(stdouterr='mytest', args=['PROPS_FILE='+self.input+'/input.properties'])

	def validate(self):
		self.assertGrep('build-output/props.txt', expr=r"baz=Hello world$")

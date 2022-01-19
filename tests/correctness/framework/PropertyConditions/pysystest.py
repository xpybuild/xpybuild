__pysys_title__   = r""" Properties - conditions in .properties files""" 
#                        ================================================================================

__pysys_purpose__ = r""" The purpose of this test is to check conditions such as <windows>, <windows, debug> 
	and complex eval strings nested within <...> blocks work when reading .properties files. 
	""" 
	
__pysys_authors__ = "bsp"
__pysys_created__ = "2021-11-18"

#__pysys_traceability_ids__ = "Bug-1234, UserStory-456" 
#__pysys_groups__           = "myGroup, disableCoverage, performance; inherit=true"
#__pysys_skipped_reason__   = "Skipped until Bug-1234 is fixed"
#__pysys_modes__            = """ lambda helper: helper.combineModeDimensions(helper.inheritedModes, helper.makeAllPrimary({'MyMode':{'MyParam':123}})) """

import pysys
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):
	def execute(self):
		self.xpybuild(stdouterr='mytest', args=[])

	def validate(self):
		self.assertDiff('build-output/props.txt', 'props.txt')

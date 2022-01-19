__pysys_title__   = r""" Target name cannot contain invalid Windows characters """ 
#                        ================================================================================

__pysys_purpose__ = r""" """ 
	
__pysys_authors__ = "bsp"
__pysys_created__ = "2021-12-17"

#__pysys_traceability_ids__ = "Bug-1234, UserStory-456" 
#__pysys_groups__           = "myGroup, disableCoverage, performance; inherit=true"
#__pysys_skipped_reason__   = "Skipped until Bug-1234 is fixed"
#__pysys_modes__            = """ lambda helper: helper.combineModeDimensions(helper.inheritedModes, helper.makeAllPrimary({'MyMode':{'MyParam':123}})) """

import pysys
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):
	def execute(self):
		self.xpybuild(buildfile='test1.xpybuild.py', stdouterr='mytest1', args=[], shouldFail=True)
		self.xpybuild(buildfile='test2.xpybuild.py', stdouterr='mytest2', args=[], shouldFail=True)

	def validate(self):
		self.assertGrep('mytest1.out', 'XPYBUILD FAILED: FAILED to prepare target <WriteFile> ${OUTPUT_DIR}/invalidchars*and<.txt: Invalid character(s) "*<" found in target name', literal=True)
		self.assertGrep('mytest2.out', 'XPYBUILD FAILED: FAILED to prepare target <WriteFile> ${OUTPUT_DIR}/trailing period.: Target name must not end in a "." or " "', literal=True)
		

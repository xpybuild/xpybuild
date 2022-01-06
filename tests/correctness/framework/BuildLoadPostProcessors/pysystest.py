__pysys_title__   = r""" BuildLoadPostProcessor - adding options and tags at the end of target parsing """ 
#                        ================================================================================

__pysys_purpose__ = r""" The purpose of this test is ... TODO.
	
	""" 
	
__pysys_authors__ = "bsp"
__pysys_created__ = "2022-01-06"

#__pysys_traceability_ids__ = "Bug-1234, UserStory-456" 
#__pysys_groups__           = "myGroup, disableCoverage, performance; inherit=true"
#__pysys_skipped_reason__   = "Skipped until Bug-1234 is fixed"

import pysys
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):
	def execute(self):
		self.xpybuild(stdouterr='targets', args=['-s', '-target.txt'])

	def validate(self):
		self.assertThatGrep('targets.out', r'<MyCustomTarget>.*tags: \[(.*)\]', 
			expected='my-post-processed-tag original-tag')

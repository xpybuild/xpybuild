__pysys_title__   = r""" The --search option """ 
#                        ================================================================================

__pysys_purpose__ = r""" The purpose of this test is ... TODO.
	
	""" 
	
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
		self.xpybuild(stdouterr='prop', args=['--search', 'PROP'])
		self.xpybuild(stdouterr='option', args=['-s', 'MyOption.*'])
		self.xpybuild(stdouterr='tag', args=['-s', 'mytag.*'])
		self.xpybuild(stdouterr='targetName', args=['-s', '/target1${DOT}txt'])
		self.xpybuild(stdouterr='targetPath', args=['-s', 'target1.txt'])
		self.xpybuild(stdouterr='targetRegex', args=['-s', 'target.*'])
	
		# just for manual inspection
		self.xpybuild(stdouterr='all', args=['-s', 'O'])

	def validate(self):
		for x in [
				'prop',
				'option',
				'tag',
				'targetName',
				'targetPath',
				'targetRegex',
				]:
			self.assertDiff(x+'.out', replace=[('defined: .*', 'defined: <path>'), (r'\\', '/')])
		
		self.logFileContents('all.out', maxLines=0)
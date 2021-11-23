__pysys_title__   = r""" Properties - experimental {...} instead of ${...} property setting  """ 
#                        ================================================================================

__pysys_purpose__ = r""" The purpose of this test is ... TODO.
	
	""" 
	
__pysys_authors__ = "bsp"
__pysys_created__ = "2021-11-23"

#__pysys_traceability_ids__ = "Bug-1234, UserStory-456" 
#__pysys_groups__           = "myGroup, disableCoverage, performance; inherit=true"
#__pysys_skipped_reason__   = "Skipped until Bug-1234 is fixed"
#__pysys_modes__            = """ lambda helper: helper.combineModeDimensions(helper.inheritedModes, helper.makeAllPrimary({'MyMode':{'MyParam':123}})) """

import pysys
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):
	def execute(self):
		self.xpybuild(stdouterr='xpybuild', args=[], env={'XPYBUILD_EXPERIMENTAL_NO_DOLLAR_PROPERTY_SYNTAX':'true'})
		self.xpybuild(stdouterr='properties', args=['--properties'], env={'XPYBUILD_EXPERIMENTAL_NO_DOLLAR_PROPERTY_SYNTAX':'true'})
		self.xpybuild(stdouterr='targets', args=['--targets'], env={'XPYBUILD_EXPERIMENTAL_NO_DOLLAR_PROPERTY_SYNTAX':'true'})
		self.xpybuild(stdouterr='options', args=['--options'], env={'XPYBUILD_EXPERIMENTAL_NO_DOLLAR_PROPERTY_SYNTAX':'true'})

	def validate(self):
		self.assertGrep('properties.out', expr=r"[$]", contains=False)
		self.assertGrep('targets.out', expr=r"[$]", contains=False, ignores=['[$][$][{]literal1'])
		self.assertGrep('options.out', expr=r"[$]", contains=False)

		self.assertGrep('xpybuild.out', expr=r"[$]", contains=False, ignores=['[$][$][{]literal1'])
		
		self.assertPathExists('build-output/output-foobar.txt')
		self.assertPathExists('build-output/escaping1-${literal1}.txt')
		self.assertPathExists('build-output/escaping2-{literal2}.txt')

		#self.assertGrep('xpybuild.out', expr=r"XXX") # if no extra verifications are needed, instead use: self.addOutcome(PASSED)

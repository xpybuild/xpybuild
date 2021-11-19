@@DEFAULT_DESCRIPTOR@@

import pysys
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):
	def execute(self):
		self.xpybuild(stdouterr='mytest', args=[])

	def validate(self):
		self.assertGrep('mytest.out', expr=r"XXX") # if no extra verifications are needed, instead use: self.addOutcome(PASSED)

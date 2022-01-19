from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		# ought to succeed; if it doesn't we have a problem
		self.xpybuild(args=['--rebuild'], stdouterr='xpybuild')

	def validate(self):
		self.addOutcome(PASSED) 
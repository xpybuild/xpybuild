from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
#		msg = self.xpybuild(shouldFail=False)
#		msg = self.xpybuild(shouldFail=False)
		msg = self.xpybuild(shouldFail=False, args=['-n'])

	def validate(self):
		pass

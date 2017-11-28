from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		msg = self.xpybuild(shouldFail=False)

	def validate(self):
		self.assertDiff('build-output/defaults.txt', 'defaults.txt')
		self.assertDiff('build-output/targetOverride.txt', 'targetOverride.txt')
		self.assertDiff('build-output/legacyTargetOverride.txt', 'legacyTargetOverride.txt')

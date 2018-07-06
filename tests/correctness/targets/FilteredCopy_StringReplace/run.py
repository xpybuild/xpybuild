from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild()

	def validate(self):
		self.assertDiff('build-output/output-default.txt', 'ref-default.txt')
		self.assertDiff('build-output/output-no-expansion.txt', 'ref-no-expansion.txt')

from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild()

	def validate(self):
		self.logFileContents('build-output/output.txt', maxLines=0, encoding='utf-8')
		self.assertDiff('build-output/output.txt', 'ref-output.txt', encoding='utf-8')

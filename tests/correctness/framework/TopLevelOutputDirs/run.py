from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild(stdouterr='xpybuild', args=['OUTPUT_DIR=%s/build-output'%self.output])
		self.logFileContents('build-output/output.txt')

	def validate(self):
		self.assertDiff(file1='build-output/output.txt', file2='ref-output.txt')
		
import shutil 
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild(args=[], stdouterr='xpybuild')

	def validate(self):
		self.logFileContents('build-output/copy-dest/test.txt', maxLines=0)
		self.logFileContents('build-output/BUILD_WORK/targets/FilteredCopy/implicit-inputs/_OUTPUT_DIR_.copy-dest.txt', maxLines=0)

		self.assertDiff('build-output/copy-dest/test.txt', 'ref-test.txt')
		self.assertDiff('build-output/copy-dest/test2.txt', 'ref-test2.txt')

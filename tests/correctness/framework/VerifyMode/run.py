from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		msg = self.xpybuild(args=['--keep-going', '--verify', '--rebuild'], shouldFail=True)
		self.logFileContents('xpybuild.out', tail=True)

	def validate(self):
		self.assertGrep(file='xpybuild.log', expr="deleted-file.txt verification error: Target dependency was deleted while it was being built: .+bar.txt", abortOnError=False)
		self.assertGrep(file='xpybuild.log', expr=".*modified-file.txt verification error: Modification date of target dependency .+src-file.txt is [0-9.]+s after the target's start time", abortOnError=False)

		# should still complete each target
		self.assertGrep(file='xpybuild.log', expr="/modified-file.txt: done in .+ seconds")
		self.assertGrep(file='xpybuild.log', expr="XPYBUILD FAILED: 2 error")
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		# must build both targets the first time
		msg = self.xpybuild(args=['--rid', 'mycopy'], stdouterr='xpybuild-initial')
		msg = self.xpybuild(args=['--rid', 'mycopy'], stdouterr='xpybuild-incremental')

	def validate(self):
		self.assertGrep(file='xpybuild-initial.log', expr="CRITICAL .*XPYBUILD SUCCEEDED: 2 built")
		self.assertGrep(file='xpybuild-incremental.log', expr="Target is not checked for up-to-dateness due to ignore-deps option: .*writefile.txt")
		self.assertGrep(file='xpybuild-incremental.log', expr="CRITICAL .*XPYBUILD SUCCEEDED: 1 built")

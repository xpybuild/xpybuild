from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest
import os

class PySysTest(XpybuildBaseTest):

	def execute(self):
		msg = self.xpybuild(args=[], expectedExitStatus='==4')

	def validate(self):
		self.assertGrep(file='xpybuild.log', expr='Test processOutputEncodingDecider called with exename=.*(cmd|echo)')
		self.assertGrep(file='xpybuild.log', expr='MyHandler.handleEnd was called')
		self.assertGrep(file='xpybuild.log', expr='ERROR .*output.txt ERROR> Hello world')
		self.assertGrep(file='xpybuild.log', expr='Target FAILED: .*Simulated error from handleEnd: Hello world')
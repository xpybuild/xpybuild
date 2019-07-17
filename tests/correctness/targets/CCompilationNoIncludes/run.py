from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		msg = self.xpybuild(shouldFail=False, args=[], buildfile='root.xpybuild.py')
		self.startProcess(self.output+'/build-output/test', [], stdout='test.out', stderr='test.err')

	def validate(self):
		self.assertGrep(file='xpybuild.out', expr="ERROR .*", contains=False)
		self.assertGrep(file='test.out', expr="Test program")

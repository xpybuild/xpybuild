from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild(args=['--depgraph', 'depgraph-output.dot'])

	def validate(self):
		self.assertDiff(file1='depgraph-output.dot', file2='ref-depgraph-output.dot')
	
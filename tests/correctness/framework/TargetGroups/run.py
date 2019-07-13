from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild(args=['${OUTPUT_DIR}/testtarget4'])

	def validate(self):
		# even though no explicit dependency, target4 depends on this via the target group
		self.assertGrep('xpybuild.log', expr='Building .*testtarget2')
		
		# sanity check that we didn't build everything
		self.assertGrep('xpybuild.log', expr='Building .*testtarget3', contains=False) 
		
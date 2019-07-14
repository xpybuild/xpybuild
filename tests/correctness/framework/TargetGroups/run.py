from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild(args=['${OUTPUT_DIR}/testtarget/'])

	def validate(self):
		# even though no explicit dependency, target4 depends on this via the target group
		self.assertGrep('xpybuild.log', expr='Building .*testtarget1b')
		self.assertGrep('xpybuild.log', expr='Building .*testtarget2a')
		self.assertGrep('xpybuild.log', expr='Building .*testtarget2b')

		# sanity check that we didn't build everything
		self.assertGrep('xpybuild.log', expr='Building .*testtarget-not-in-group', contains=False) 

		# check we don't have any duplicate entries
		self.assertGrep('xpybuild.log', expr='Target <Copy> .*testtarget/ .*depends on: .*testtarget1a, .*testtarget1b, .*testtarget2a, .*testtarget2b$') 
		
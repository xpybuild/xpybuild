from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild(args=['--timefile', 'timefile-output', 
			'--cpu-stats'])

	def validate(self):
		self.assertGrep('xpybuild.log', expr='Critical Path is:')
		
		self.assertGrep('timefile-output.csv', expr='Target,Time,Cumulative,Critical Path')
		self.assertGrep('timefile-output.csv', expr='${OUTPUT_DIR}/testtarget4/,', literal=True)

		self.assertGrep('timefile-output.dot', expr='testtarget2b -> .*testtarget4')
		
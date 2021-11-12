from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		msg = self.xpybuild(args=[], shouldFail=True)
		self.logFileContents('xpybuild.out', tail=True)

	def validate(self):
		self.assertGrep(file='xpybuild.log', expr='TEST FAILED', contains=False)

		self.assertOrderedGrep(file='xpybuild.log', exprList=[
		'WARNING .* - Target <MyTarget> .*mytarget/ failed on retry #1, will retry after 1 seconds backoff',
		'INFO .*- Target clean is deleting directory: .*mytarget',
		'WARNING .*failed on retry #2, will retry after 2 seconds backoff',
		'WARNING .*- Target <MyTarget> .*mytarget/ failed after 2 retries',
		'ERROR .*- Target FAILED: .*mytarget/ : Target FAILED due to Exception: Simulated target failure',
		'Traceback ',
		': Target FAILED due to Exception: Simulated target failure',
		])

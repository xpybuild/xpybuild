from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		# force single-threaded, since for most fomatters buffering is disabled in single-threaded mode, but teamcity 
		# should override that to allow us to avoid logging errors to stdout for potentially retry-able failures
		msg = self.xpybuild(args=['--format=teamcity', '-j1'], shouldFail=True)
		self.logFileContents('xpybuild.out', tail=True)

	def validate(self):
		self.assertGrep(file='xpybuild.log', expr='TEST FAILED', contains=False)

		# Check that _earlier_ failures don't get logged in a way that could cause TeamCity to report a build failure 
		# even if the target succeeds on retry. The final one, of course, is OK. 
		self.assertLineCount('xpybuild.out', "^##teamcity.message.*Error logged by target.*status='ERROR'", condition='==1')
		# But the .log file contains everything
		self.assertLineCount('xpybuild.log', " ERROR .*Error logged by target", condition='==3')

		self.assertOrderedGrep(file='xpybuild.log', exprList=[
			'ERROR .* - Error logged by target',
			'WARNING .* - Target <MyTarget> .*mytarget/ failed on attempt #1, will retry after 1 seconds backoff',
			'INFO .*- Target clean is deleting directory: .*mytarget',
			'WARNING .*failed on attempt #2, will retry after 2 seconds backoff',
			'WARNING .*- Target <MyTarget> .*mytarget/ failed even after 2 retries',
			'ERROR .*- Target FAILED: .*mytarget/ : Target FAILED due to Exception: Simulated target failure',
			'Traceback ',
			': Target FAILED due to Exception: Simulated target failure',
		])

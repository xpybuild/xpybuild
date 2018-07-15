from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
#		msg = self.xpybuild(shouldFail=False)
#		msg = self.xpybuild(shouldFail=False)
		msg = self.xpybuild(shouldFail=False, args=['-n'])

	def validate(self):
		self.assertGrep(file='xpybuild.out', expr="ERROR .*", contains=False)
		targets = int(self.getExprFromFile('xpybuild.log', 'XPYBUILD SUCCEEDED: ([0-9]+) built '))
		
		deps = float(self.getExprFromFile('xpybuild.log', 'dependency resolution took ([0-9.]+) s'))
		total = float(self.getExprFromFile('xpybuild.log', 'Completed .*build .*after ([0-9.]+) s'))
		# this should be a tiny, trivial operation
		self.reportPerformanceResult(1000*deps/targets, 'Dependency resolution time per Copy target', 'ms')
		# with the -n option only up-to-dateness checking happens in build phase, so that's what we're measuring here
		self.reportPerformanceResult(1000*(total-deps)/targets, 'Up-to-date checking per Copy target', 'ms')

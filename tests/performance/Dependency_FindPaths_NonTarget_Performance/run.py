from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.mkdir('input-files')
		for i in range(256+1):
			open(self.output+'/input-files/input-%d.txt'%i, 'w').close()
	
		msg = self.xpybuild(shouldFail=False, args=['-n', '-j1'], stdouterr='xpybuild-st')
		#msg = self.xpybuild(shouldFail=False, args=['-n', '-J'], stdouterr='xpybuild-mt')

	def validate(self):
		for stdouterr in [
				#'xpybuild-mt', 
				'xpybuild-st']:
			self.assertGrep(file=stdouterr+'.out', expr="ERROR .*", contains=False)
			targets = int(self.getExprFromFile(stdouterr+'.log', 'XPYBUILD SUCCEEDED: ([0-9]+) built '))
			
			deps = float(self.getExprFromFile(stdouterr+'.log', 'dependency resolution took ([0-9.]+) s'))
			total = float(self.getExprFromFile(stdouterr+'.log', 'Completed .*build .*after ([0-9.]+) s'))

			
			if stdouterr == 'xpybuild-mt':
				statkey = 'multi-threaded'
			else:
				statkey = 'single-threaded'

			# this should be a tiny, trivial operation
			self.reportPerformanceResult(float(targets)/deps, 'Dependency resolution rate for FindPaths(non-target) Copy target %s'%statkey, '/s')
			# with the -n option only up-to-dateness checking happens in build phase, so that's what we're measuring here
			self.reportPerformanceResult(float(targets)/(total-deps), 'Up-to-date checking rate for FindPaths(non-target) Copy target %s'%statkey, '/s')

		# useful to check that the os.stat optimization is taking effect; given this test 
		# uses a small set of input files it's much less sensitive to the cost of os.stat than 
		# a real build would be so checking this explicitly is helpful
		self.assertThat('0 == %s', self.getExprFromFile('xpybuild-st.log', "Entries in path stat cache after dependency resolution phase: ([0-9]+)"))
		
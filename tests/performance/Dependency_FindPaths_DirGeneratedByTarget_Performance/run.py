from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.mkdir('input-files')
		for i in range(256+1):
			open(self.output+'/input-files/input-%d.txt'%i, 'w').close()
		
		msg = self.xpybuild(shouldFail=False, args=['-n', '-j1'], stdouterr='xpybuild-st')
		msg = self.xpybuild(shouldFail=False, args=['-n', '-J'], stdouterr='xpybuild-mt')

	def validate(self):
		for stdouterr in ['xpybuild-mt', 'xpybuild-st']:
			self.assertGrep(file=stdouterr+'.out', expr="ERROR .*", contains=False)
			targets = int(self.getExprFromFile(stdouterr+'.log', 'XPYBUILD SUCCEEDED: ([0-9]+) built '))
			
			deps = float(self.getExprFromFile(stdouterr+'.log', 'dependency resolution took ([0-9.]+) s'))
			total = float(self.getExprFromFile(stdouterr+'.log', 'Completed .*build .*after ([0-9.]+) s'))

			
			if stdouterr == 'xpybuild-mt':
				# These are just for comparing with pre v15
				self.reportPerformanceResult(1000*1000*1000*deps/targets, 'Dependency resolution time per Copy target', 'ns')
				self.reportPerformanceResult(1000*1000*1000*(total-deps)/targets, 'Up-to-date checking per Copy target', 'ns')
				self.log.info('')
				statkey = 'multi-threaded'
			else:
				statkey = 'single-threaded'

			# this should be a tiny, trivial operation
			self.reportPerformanceResult(float(targets)/deps, 'Dependency resolution rate for FindPaths(DirGeneratedByTarget) Copy target %s'%statkey, '/s')
			# with the -n option only up-to-dateness checking happens in build phase, so that's what we're measuring here
			self.reportPerformanceResult(float(targets)/(total-deps), 'Up-to-date checking rate for FindPaths(DirGeneratedByTarget) Copy target %s'%statkey, '/s')


from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest
import shutil

class PySysTest(XpybuildBaseTest):
	TARGETS = 2000
	THREADS = 4 # aim to take similar amount of time regardless of machine size

	def execute(self):
		self.xpybuild(shouldFail=False, args=['--workers', str(self.THREADS), 'CPP_FILES=%s'%self.TARGETS, '-n'], buildfile='root.xpybuild.py', stdouterr='xpybuild-dep-check')
		self.xpybuild(shouldFail=False, args=['--workers', str(self.THREADS), 'CPP_FILES=%s'%self.TARGETS, '-n'], buildfile='root.xpybuild.py', stdouterr='xpybuild-dep-check-no-op')
		self.xpybuild(shouldFail=False, args=['--workers', str(self.THREADS), 'CPP_FILES=%s'%self.TARGETS], buildfile='root.xpybuild.py', stdouterr='xpybuild-build')
		self.xpybuild(shouldFail=False, args=['--workers', str(self.THREADS), 'CPP_FILES=%s'%self.TARGETS], buildfile='root.xpybuild.py', stdouterr='xpybuild-build-no-op')
		# this is large and not useful for so delete it
		try:
			shutil.rmtree(self.output+'/build-output/BUILD_WORK')
		except Exception as e:
			self.log.warn('Failed to purge BUILD_WORK: %s', e)

	def validate(self):
		results = {}
		for f in ['xpybuild-dep-check', 'xpybuild-dep-check-no-op', 'xpybuild-build', 'xpybuild-build-no-op']:
			#self.assertGrep(file=f+'.log', expr="ERROR .*", contains=False)
			self.logFileContents(f+'.out', tail=True, maxLines=2)
			deps = float(self.getExprFromFile(f+'.out', 'dependency resolution took ([0-9.]+) s'))
			build = float(self.getExprFromFile(f+'.out', 'Completed .*build .*after ([0-9.]+) s'))-deps
			
			self.log.info('%s: deps took %0.1fs, build took %0.1fs', f, deps, build)
			
			results[f+'.deps'] = deps or 1e-10 # avoid by by zero
			results[f+'.build'] = build or 1e-10
		self.assertGrep(file='xpybuild-build-no-op.log', expr="<NO TARGETS> built")

		self.reportPerformanceResult(self.TARGETS / results['xpybuild-dep-check.deps'], 'Dependency resolution rate for C++ target', '/s')
		self.reportPerformanceResult(self.TARGETS / results['xpybuild-build.build'], 'Build rate for C++ target', '/s')

		# should be pretty good
		self.reportPerformanceResult(self.TARGETS / (results['xpybuild-build-no-op.deps']+results['xpybuild-build-no-op.build']), 'Dependency resolution and uptodate checking no-op incremental build rate for C++ target', '/s')
		self.log.info('')

		# legacy numbers for comparison with old versions (per thread is actually not that helpful given it scales little if not at all, so ignore that)
		normfactor = self.TARGETS/(float(self.THREADS)*1000*1000*1000)
		self.reportPerformanceResult(results['xpybuild-dep-check.deps']/normfactor, 'Dependency resolution time per C++ target', 'ns')
		self.reportPerformanceResult(results['xpybuild-build.build']/normfactor, 'Build time per C++ target', 'ns')
		self.reportPerformanceResult((results['xpybuild-build-no-op.deps']+results['xpybuild-build-no-op.build'])/normfactor, 'Incremental build and dependency resolution time per C++ target', 'ns')

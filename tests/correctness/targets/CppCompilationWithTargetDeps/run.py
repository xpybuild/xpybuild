import shutil 
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def xpybuild(self, **kwargs):
		super(PySysTest, self).xpybuild(**kwargs)
		selectedtargets = 'build-output/BUILD_WORK/targets/selected-targets.txt'
		shutil.copyfile(self.output+'/'+selectedtargets, self.output+'/selected-targets-%s.txt'%kwargs['stdouterr'])
		
		# make sure none of them are different
		self.assertDiff(file1=self.output+'/selected-targets-%s.txt'%'xpybuild', file2 = self.output+'/selected-targets-%s.txt'%kwargs['stdouterr'])

	def execute(self):

		shutil.copytree(self.input, self.output+'/input')
		self.xpybuild(shouldFail=False, args=['--keep-going'], buildfile=self.output+'/input/root.xpybuild.py', stdouterr='xpybuild')
		
		self.xpybuild(shouldFail=False, args=[], buildfile=self.output+'/input/root.xpybuild.py', stdouterr='xpybuild-incremental-noop')

		# check we detect changes in generated headers
		def touchfile(p): 
			assert os.path.exists(self.output+'/'+p), self.output+'/'+p
			os.utime(self.output+'/'+p, None)
		touchfile('build-output/BUILD_WORK/targets/Copy/implicit-inputs/_OUTPUT_DIR_.my-generated-include-files.txt') # stamp file for /generatedpath
		touchfile('build-output/my-generated-include-files/generatedpath/test3.h')
		
		touchfile('build-output/my-generated-include-files2/generatedpath/test3.h')
		self.xpybuild(shouldFail=False, args=[], buildfile=self.output+'/input/root.xpybuild.py', stdouterr='xpybuild-incremental-generated-headers-changed')

		touchfile('build-output/test-generated.cpp')
		self.xpybuild(shouldFail=False, args=[], buildfile=self.output+'/input/root.xpybuild.py', stdouterr='xpybuild-incremental-generated-cpp-changed')

		touchfile('input/include/somepath/test1.h')
		self.xpybuild(shouldFail=False, args=['-j1'], buildfile=self.output+'/input/root.xpybuild.py', stdouterr='xpybuild-incremental-static-headers-changed')

		touchfile('input/test.cpp')
		self.xpybuild(shouldFail=False, args=[], buildfile=self.output+'/input/root.xpybuild.py', stdouterr='xpybuild-incremental-static-cpp-changed')

	def validate(self):
		# include-file support is currently not provided (was slightly present in 1.14 but very broken), but could be uncommented if we ever decide to add it
	
		self.assertGrep(file='xpybuild.out', expr="ERROR .*", contains=False)
		self.logFileContents('xpybuild.log', includes=['Target <Cpp> .*depends on: .*'])
		self.logFileContents('xpybuild-incremental-noop.log', includes=['Target <Cpp> .*depends on: .*'])

		# check for correct target dependencies
		for t in [
				'target-cpp-and-include-dir',
				'target-cpp',

		]:
			self.assertGrep(file='selected-targets-xpybuild.txt', expr='Target <Cpp> .*%s[) ].*depends on: .*OUTPUT_DIR./test-generated.cpp'%t)

		for t in [
				'target-include-file',

		]:
			self.assertGrep(file='selected-targets-xpybuild.txt', expr='Target <Cpp> .*%s[) ].*depends on: .*OUTPUT_DIR.*/test3.h'%t)
		for t in [
				'target-cpp-and-include-dir',
				'target-include-dir',

		]:
			self.assertGrep(file='selected-targets-xpybuild-incremental-noop.txt', expr='Target <Cpp> .*%s[) ].*depends on: .*OUTPUT_DIR.*/my-generated-include-files/'%t)


		for t in [
				'no-target-deps',
				'target-cpp-and-include-dir',
				'target-cpp',
				'target-include-dir',
				'target-include-file',
			]:
			makedep = 'build-output/BUILD_WORK/targets/makedepend-cache/objectname(_OUTPUT_DIR_.%s).makedepend'%t
			self.assertOrderedGrep(file=makedep, exprList=[
				# deplist - from running makedepends
				'test3.h',
				'test1.h',
				'test2.h',
				])
			self.assertLineCount(makedep, expr='test(-generated)?.cpp', condition='==0')
		self.logFileContents(makedep, maxLines=50)
		
		for log, expectedchanges in [
			('incremental-generated-headers-changed', ['target-cpp-and-include-dir', 
				'target-include-dir', 
				'target-include-file', 
			]),
			('incremental-generated-cpp-changed', [
				'target-cpp-and-include-dir', 'target-cpp']),
		]:
			self.log.info('')
			for t in expectedchanges:
				self.assertGrep('xpybuild-'+log+'.log', expr=' Building .*%s'%t)
			self.assertLineCount('xpybuild-'+log+'.log', expr=' Building ', condition='==%d'%len(expectedchanges))
			
		self.assertGrep('xpybuild-%s.log'%'incremental-noop', 
			expr='Recalculating .* dependencies of <Cpp>.*', contains=False)
			
		# these should build everything
		self.assertGrep('xpybuild-incremental-static-headers-changed.log', expr='already up-to-date: .*Cpp', contains=False)
		self.assertGrep('xpybuild-incremental-static-cpp-changed.log', expr='already up-to-date: .*Cpp', contains=False)

		# incremental should not rebuild anything
		self.assertGrep(file='xpybuild-incremental-noop.out', expr="XPYBUILD SUCCEEDED: <NO TARGETS> built")

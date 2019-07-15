import shutil 
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def xpybuild(self, **kwargs):
		super(PySysTest, self).xpybuild(**kwargs)
		selectedtargets = 'build-output/BUILD_WORK/targets/selected-targets.txt'
		shutil.copyfile(self.output+'/'+selectedtargets, self.output+'/selected-targets-%s.txt'%kwargs['stdouterr'])

	def execute(self):

		shutil.copytree(self.input, self.output+'/input')
		self.xpybuild(shouldFail=False, args=['--keep-going'], buildfile=self.output+'/input/root.xpybuild.py', stdouterr='xpybuild')
		
		self.xpybuild(shouldFail=False, args=[], buildfile=self.output+'/input/root.xpybuild.py', stdouterr='xpybuild-incremental-noop')
		# TODO: if this was working properly first incremental build would do nothing
		self.xpybuild(shouldFail=False, args=[], buildfile=self.output+'/input/root.xpybuild.py', stdouterr='xpybuild-incremental-noop2')

		# check we detect changes in generated headers
		def touchfile(p): 
			assert os.path.exists(self.output+'/'+p), self.output+'/'+p
			os.utime(self.output+'/'+p, None)
		touchfile('build-output/BUILD_WORK/targets/implicit-inputs/_OUTPUT_DIR_.my-generated-include-files.txt') # stamp file for /generatedpath
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
		# everything commented out here is due to a bug in 1.14
	
		self.assertGrep(file='xpybuild.out', expr="ERROR .*", contains=False)
		self.logFileContents('xpybuild.log', includes=['Target <Cpp> .*depends on: .*'])
		self.logFileContents('xpybuild-incremental-noop.log', includes=['Target <Cpp> .*depends on: .*'])

		for t in [
				'target-cpp-and-include-dir',
				'target-cpp-and-include-file',
				'target-cpp',

		]:
			self.assertGrep(file='selected-targets-xpybuild.txt', expr='Target <Cpp> .*%s[) ].*depends on: .*OUTPUT_DIR./test-generated.cpp'%t)

		for t in [
				#'target-cpp-and-include-file',

				#'target-include-file',

		]:
			self.assertGrep(file='selected-targets-xpybuild.txt', expr='Target <Cpp> .*%s[) ].*depends on: .*OUTPUT_DIR.*/test3.h'%t)
		for t in [
				'target-cpp-and-include-dir',
				#'target-include-dir',

		]:
			#self.assertGrep(file='xpybuild.log', expr='Target <Cpp> .*%s[) ].*depends on: .*OUTPUT_DIR.*/my-generated-include-files/'%t)
			self.assertGrep(file='selected-targets-xpybuild-incremental-noop.txt', expr='Target <Cpp> .*%s[) ].*depends on: .*OUTPUT_DIR.*/my-generated-include-files/'%t)


		for t in [
				'no-target-deps',
				#'target-cpp-and-include-dir',
				'target-cpp-and-include-file',
				'target-cpp',
				#'target-include-dir',
				#'target-include-file',
			]:
			makedep = 'build-output/BUILD_WORK/targets/objectname(_OUTPUT_DIR_.%s).makedepend'%t
			self.assertOrderedGrep(file=makedep, exprList=[
				# deplist - from running makedepends
				'test3.h',
				'test1.h',
				'test2.h',
				
				'^$', # blank line
				
				# depsources - underlying dependencies of source files
				'test(-generated)?.cpp'
				])
			self.assertLineCount(makedep, expr='test(-generated)?.cpp', condition='==1', ignores=['MakeDepend.*']) # check no duplicates
		self.logFileContents(makedep, maxLines=50)
		
		# TODO: add from other targets
		for log, expectedchanges in [
			('incremental-generated-headers-changed', ['target-cpp-and-include-file', 'target-cpp-and-include-dir', 
				#'target-include-dir', 'target-include-file',
			]),
			('incremental-generated-cpp-changed', ['target-cpp-and-include-file', 'target-cpp-and-include-dir', 'target-cpp']),
		]:
			self.log.info('')
			for t in expectedchanges:
				self.assertGrep('xpybuild-'+log+'.log', expr=' Building .*%s'%t)
			self.assertLineCount('xpybuild-'+log+'.log', expr=' Building ', condition='==%d'%len(expectedchanges))
		# these should build everything
		self.assertGrep('xpybuild-incremental-static-headers-changed.log', expr='already up-to-date: .*Cpp', contains=False)
		self.assertGrep('xpybuild-incremental-static-cpp-changed.log', expr='already up-to-date: .*Cpp', contains=False)

		# incremental should not rebuild anything
		#self.assertGrep(file='xpybuild-incremental-noop.out', expr="XPYBUILD SUCCEEDED: <NO TARGETS> built")
		self.assertGrep(file='xpybuild-incremental-noop2.out', expr="XPYBUILD SUCCEEDED: <NO TARGETS> built")
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		msg = self.xpybuild(shouldFail=False)
		self.xpybuild(stdouterr='xpybuild-options', args=['--options'])

	def validate(self):
		self.assertDiff('build-output/defaults.txt', 'defaults.txt', abortOnError=False)
		self.assertDiff('build-output/targetOverride.txt', 'targetOverride.txt', abortOnError=False)
		self.assertDiff('build-output/legacyTargetOverride.txt', 'legacyTargetOverride.txt', abortOnError=False)

		self.assertGrep(file='xpybuild.out', expr="targetOverrideBoth.txt mergeOptions testoption.targetOverride=expectedval")

		self.assertGrep(file='xpybuild.out', expr="PathSet._resolveUnderlyingDependencies got options")

		self.assertGrep(file='xpybuild.out', expr="Cannot read the value of basetarget.targetOptions during the initialization phase of the build", literal=True)
		self.assertGrep(file='xpybuild.out', expr="ERROR .*", contains=False)

		self.assertGrep(file='xpybuild-options.out', expr="testoption.default = expectedval")
		self.assertGrep(file='xpybuild-options.out', expr="testoption.globalOverride = expectedval")
		self.assertGrep(file='xpybuild-options.out', expr="testoption2.empty = $")
		
		self.assertGrep(file='xpybuild-options.out', expr="Traceback", contains=False)
		
		
		self.logFileContents('build-output/BUILD_WORK/targets/MyTarget/implicit-inputs/_OUTPUT_DIR_.defaults.txt.txt', tail=True)
		
		# default options shouldn't contain any objects with no nice repr representation, 
		# least in the implicit inputs file whcih is used to decide rebuilding
		self.assertGrep(file='build-output/BUILD_WORK/targets/MyTarget/implicit-inputs/_OUTPUT_DIR_.defaults.txt.txt', expr="at 0x", contains=False)
		# check we did include a wide range of options as a result of the addHashableImplicitInputOption call
		self.assertGrep(file='build-output/BUILD_WORK/targets/MyTarget/implicit-inputs/_OUTPUT_DIR_.defaults.txt.txt', expr="native.")

		self.assertGrep(file='build-output/BUILD_WORK/targets/MyTarget/implicit-inputs/_OUTPUT_DIR_.defaults.txt.txt', expr="^None$", contains=False) # none items should be filtered  out
		self.assertGrep(file='build-output/BUILD_WORK/targets/MyTarget/implicit-inputs/_OUTPUT_DIR_.defaults.txt.txt', expr="addHashableImplicitInput str expectedval")
		self.assertGrep(file='build-output/BUILD_WORK/targets/MyTarget/implicit-inputs/_OUTPUT_DIR_.defaults.txt.txt', expr="testoption.default")

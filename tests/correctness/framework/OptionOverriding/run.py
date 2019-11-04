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
		
		# default options shouldn't contain any objects with no nice string representation
		self.assertGrep(file='xpybuild-options.out', expr="at 0x", contains=False)
		
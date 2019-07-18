from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		implicitinputs = 'build-output/BUILD_WORK/targets/CustomTarget/implicit-inputs/_OUTPUT_DIR_.output.txt.txt'
		msg = self.xpybuild(stdouterr='xpy-initial', args=['MY_PROP1=val1', 'MY_PROP2=val2', 'MY_PROP3=val3'])
		self.assertGrep(implicitinputs, expr='addHashableImplicitInput-string=val1', abortOnError=False)
		self.assertGrep(implicitinputs, expr='addHashableImplicitInput-callable=val2', abortOnError=False)
		
		msg = self.xpybuild(stdouterr='xpy-change-string', args=['MY_PROP1=val1MOD', 'MY_PROP2=val2', 'MY_PROP3=val3'])
		self.assertGrep(implicitinputs, expr='addHashableImplicitInput-string=val1MOD', abortOnError=False)
		
		msg = self.xpybuild(stdouterr='xpy-change-callable', args=['MY_PROP1=val1MOD', 'MY_PROP2=val2MOD', 'MY_PROP3=val3'])
		self.assertGrep(implicitinputs, expr='addHashableImplicitInput-callable=val2MOD', abortOnError=False)
		
		msg = self.xpybuild(stdouterr='xpy-change-option', args=['MY_PROP1=val1MOD', 'MY_PROP2=val2MOD', 'MY_PROP3=val3MOD'])
		self.assertGrep(implicitinputs, expr='option myoption=\'val3MOD\'', abortOnError=False)
		
		msg = self.xpybuild(stdouterr='xpy-nochange', args=['MY_PROP1=val1MOD', 'MY_PROP2=val2MOD', 'MY_PROP3=val3MOD'])
		self.logFileContents(implicitinputs)

	def validate(self):
		for f in ['initial', 'change-string', 'change-callable', 'change-option']:
			self.assertGrep(file='xpy-%s.out'%f, expr="XPYBUILD SUCCEEDED: 1 built", abortOnError=False)
		self.assertGrep(file='xpy-nochange.out', expr="XPYBUILD SUCCEEDED: <NO TARGETS> built", abortOnError=False)
		
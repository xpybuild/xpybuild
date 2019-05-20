from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild(buildfile=self.input+'/errors.xpybuild.py', shouldFail=True, stdouterr='errors')
		self.xpybuild(buildfile=self.input+'/warnings.xpybuild.py', shouldFail=False, stdouterr='warnings')
		self.xpybuild(buildfile=self.input+'/warnings-regexIgnore.xpybuild.py', shouldFail=False, stdouterr='warnings-regexIgnore')

	def validate(self):
		self.assertGrep('errors.log', expr=r'Target FAILED: <Jar> .*test-errors.jar : 2 errors, first is: error: cannot find symbol: <method foo.*> in <class JavaErrors> at .*JavaErrors.java:5')
		self.assertGrep('errors.log', expr=r'foo();', literal=True)
		self.assertGrep('errors.log', expr=r'bar();', literal=True)
		
		self.assertGrep('warnings.log', expr=r'2 javac WARNINGS in .*test-warnings/ - see .*warnings.txt; first is: .*redundant cast')

		self.assertGrep('warnings-regexIgnore.log', expr=r'javac WARNINGS', contains=False)
		self.assertGrep('warnings-regexIgnore.log', expr=r' WARN .*', contains=False)

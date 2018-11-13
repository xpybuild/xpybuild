from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest
import os

class PySysTest(XpybuildBaseTest):

	def execute(self):
		msg = self.xpybuild(shouldFail=False, args=[], env={'UNSET_ENV':'Bar', 'SET_ENV':'Baz', 'OVERRIDE_ENV':'True'})

	def validate(self):
		self.assertGrep(file='xpybuild.out', expr="ERROR .*", contains=False)
		self.assertGrep(file=self.output+'/build-output/output.txt', expr='UNSET_ENV', contains=False)
		self.assertGrep(file=self.output+'/build-output/output.txt', expr='SET_ENV=Baz')
		self.assertGrep(file=self.output+'/build-output/output.txt', expr='ADD_ENV=Foo')
		self.assertGrep(file=self.output+'/build-output/output.txt', expr='OVERRIDE_ENV=Quuxx')
		

from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild(buildfile=self.input+'/source_target.xpybuild.py', shouldFail=False, stdouterr='source_target')

	def validate(self):
		self.assertOrderedGrep('source_target.log', exprList=['"javac"', '"-source"', '"7"', '"-target"', '"8"',  '"-encoding"'])

from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild(buildfile=self.input+'/root.xpybuild.py')

	def validate(self):
		pass # just check for successful compilation
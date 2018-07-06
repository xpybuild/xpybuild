from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		msg = self.xpybuild(shouldFail=True)
		self.assertThat('"Some of the specified mappers did not get used at all during the copy" in "%s"', msg.replace('"',''))
		self.assertThat('"StringReplaceLineMapper" in "%s"', msg.replace('"',''))

	def validate(self):
		pass
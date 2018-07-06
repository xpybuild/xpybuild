from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		msg = self.xpybuild(shouldFail=False, args=['DOCKER_PATH=/usr/bin', 'DOCKER_HOST=', 'DOCKER_REPO=', 'DOCKER_USER='])

	def validate(self):
		self.assertGrep(file='xpybuild.out', expr="ERROR .*", contains=False)
		

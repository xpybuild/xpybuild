from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild()

	def validate(self):
		self.assertDiff('build-output/no-mappers.txt', self.input+'/input.txt')
		self.assertDiff('build-output/empty-mappers.txt', self.input+'/input.txt')
		self.assertDiff('build-output/unused-mapper.txt', self.input+'/input.txt')

		self.assertGrep('build-output/working-mapper.txt', expr='AA bb cc')

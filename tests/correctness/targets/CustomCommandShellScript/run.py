from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest
import os

class PySysTest(XpybuildBaseTest):

	def execute(self):
		if not IS_WINDOWS: self.skipTest('only needed on Windows') # since it's for testing \\?\ long path support
		msg = self.xpybuild(args=[])

	def validate(self):
		self.assertGrep(file='build-output/output.txt', expr='Hello world')
		# check that \\?\ hasn't been added by the PathSet wrapper to the argument; also confirms we're normalizing to lowercase
		self.assertGrep(file='build-output/output.txt', expr='Hello world: [a-z]:')

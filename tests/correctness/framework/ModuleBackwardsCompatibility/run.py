from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest
import shutil, re, os

class PySysTest(XpybuildBaseTest):
	def execute(self):
		# build only the target we're interested in - this ensures the dependencies are correct
		self.xpybuild()

	def validate(self):
		self.addOutcome(PASSED) # absence of a build failure is sufficient here
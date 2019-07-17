from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest
import shutil, re, os

class PySysTest(XpybuildBaseTest):
	def execute(self):
		# build only the target we're interested in - this ensures the dependencies are correct
		self.xpybuild(args=['${OUTPUT_DIR}/CopyFromTargetsWithinDir/', '${OUTPUT_DIR}/CopyFromTargetsWithinDir-FindPaths/'])

	def validate(self):
		self.assertPathExists('build-output/CopyFromTargetsWithinDir-FindPaths/foo1.txt')
		self.assertPathExists('build-output/CopyFromTargetsWithinDir-FindPaths/dirA/dirB/foo2.txt')
		self.assertPathExists('build-output/CopyFromTargetsWithinDir-FindPaths/dirC/foo3.txt', exists=False)
		
		# without FindPaths it should succeed and be created, but there won't be anything in it because 
		# this pathset resolves to just the parent dir - which is necessary for FindPaths to work, and also 
		# for C++ include directories
		self.assertThat('[] == os.listdir(%s)', repr(self.output+'/build-output/CopyFromTargetsWithinDir/'))
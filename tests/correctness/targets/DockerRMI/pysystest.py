__pysys_title__   = r""" Docker - rmi image cleanup errors are not fatal """ 
#                        ================================================================================
__pysys_purpose__ = r""" """ 
	
__pysys_authors__ = "bsp"
__pysys_created__ = "2022-04-11"
#__pysys_skipped_reason__   = "Skipped until Bug-1234 is fixed"

import shutil
import pysys
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):
	def execute(self):
		DOCKER_EXE = shutil.which('docker')
		if not DOCKER_EXE: self.skipTest('Cannot test docker unless docker is on PATH')
		self.xpybuild(stdouterr='mytest', args=['--clean', 'DOCKER_EXE='+DOCKER_EXE])

	def validate(self):
		self.assertGrep('mytest.log', expr=r"ERROR", contains=False)
		self.assertGrep('mytest.log', expr=r"WARN", contains=False)

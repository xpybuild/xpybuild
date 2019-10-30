from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest
import shutil, re

class PySysTest(XpybuildBaseTest):
	def execute(self):
		self.mkdir('findpaths/subdir')
		self.write_text('findpaths/a', 'o')
		self.write_text('findpaths/b', 'o')

		self.mkdir('dirbased')
		self.write_text('dirbased/a', 'o')
		self.write_text('dirbased/b', 'o')
	
		self.xpybuild(args=[], stdouterr='1-orig')
		self.xpybuild(args=['-k'], stdouterr='2-noop')

		# touch these files
		self.wait(0.1)
		self.write_text('findpaths/b', 'xxx')
		self.write_text('dirbased/b', 'xxx')

		self.xpybuild(args=['-k'], stdouterr='3-detect-changes')

	def validate(self):
		self.assertGrep('2-noop.log', expr='Target is already up-to-date: .*dirbased-out/')
		self.assertGrep('2-noop.log', expr='Target is already up-to-date: .*findpaths-out/')
	
		self.assertGrep('3-detect-changes.log', expr='Up-to-date check: .*dirbased-out/ must be rebuilt because input file ".*b" is newer than ".+"')
		self.assertGrep('3-detect-changes.log', expr='Up-to-date check: .*findpaths-out/ must be rebuilt because input file ".*b" is newer than ".+"')
		
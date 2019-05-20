from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild()

	def validate(self):
		self.logFileContents('build-output/output.txt', maxLines=0, encoding='utf-8')
		self.assertDiff('build-output/output.txt', 'ref-output.txt', encoding='utf-8')

		# ensure all headers are present even after jar executable has changed them
		manifest = 'build-output/unpacked/META-INF/MANIFEST.MF'
		self.assertGrep(manifest, expr=' xxxxx+_') # value with continuation
		self.assertGrep(manifest, expr='Implementation-Title: *My title')
		self.assertGrep(manifest, expr='Main-Class: *my.main')
		self.assertGrep(manifest, expr='Header-2: *value 2')
		self.assertGrep(manifest, expr='Header-3: *value 3 xxxxxxx')

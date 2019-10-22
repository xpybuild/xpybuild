import shutil 
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild(args=[], stdouterr='xpybuild')

	def validate(self):
		i18n = chr(163)
		self.assertGrep('build-output/writefile-customized.foo.yaml', expr=f'Text is: {i18n}', encoding='iso-8859-1')
		self.assertGrep('build-output/writefile-default.yaml', expr=f'Text is: {i18n}', encoding='utf-8')
		self.assertGrep('build-output/copy-customized.json', expr=f'Replaced text is: {i18n}', encoding='iso-8859-1')
		self.assertGrep('build-output/copy-default.json', expr=f'Replaced text is: {i18n}', encoding='utf-8')

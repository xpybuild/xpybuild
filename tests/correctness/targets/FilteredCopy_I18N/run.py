import io, codecs
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild(args=[], stdouterr='xpybuild')

	def validate(self):
		i18n = chr(163)
		self.assertGrep('build-output/writefile-customized.foo.yaml', expr=f'Text is: {i18n}', encoding='iso-8859-1')
		self.assertGrep('build-output/writefile-default.yaml', expr=f'Text is: {i18n}', encoding='utf-8')
		self.assertGrep('build-output/writefile-binary.bin', expr=f'Text is: {i18n}', encoding='utf-8')
		self.assertGrep('build-output/copy-customized.json', expr=f'Replaced text is: {i18n}', encoding='iso-8859-1')
		self.assertGrep('build-output/copy-default.json', expr=f'Replaced text is: {i18n}', encoding='utf-8')

		# check that this file didn't get corrupted during copying
		with io.open(self.output+'/build-output/copy-compressed.jpg', 'rb') as f:
			self.assertEval('{actual} == {expected}', 
				expected=repr(codecs.encode(f'Text is: {i18n}'.encode('utf-8'), 'bz2_codec')), actual=repr(f.read())
			)
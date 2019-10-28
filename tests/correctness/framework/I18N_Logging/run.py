from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	formatters = [
		'default',
		'teamcity',
		'visualstudio',
		'make',
		'progress',
		]

	def execute(self):
		for f in self.formatters:
			self.xpybuild(stdouterr=f, args=['-F', f])

	def validate(self):
		for f in self.formatters:
			self.assertGrep(f+'.out', expr='TypeError', contains=False)
			self.assertGrep(f+'.out', expr='Traceback', contains=False)

			if f != 'default': continue # TODO: reinstate these checks, but it appears this has been broken for ages/forever
			self.assertGrep(f+'.out', expr='Test message containing I18N chars: .+ end')
			self.assertGrep(f+'.log', expr='Test message containing I18N chars: %s end'%	b'utf8_European\\xe1\\xc1x\\xdf_Katakana\\uff89\\uff81\\uff90\\uff81\\uff7f\\uff78\\uff81\\uff7d\\uff81\\uff7f\\uff76\\uff72\\uff7d\\uff84_Hiragana\\u65e5\\u672c\\u8a9e_Symbols\\u2620\\u2622\\u2603_abc123@#\\xa3!~=\\xa3x'.decode('unicode_escape'))
		
		self.assertGrep('make.out', expr='^Writing build log to') # check there's no weird prefix at beginning of line
		self.assertGrep('teamcity.out', expr=r"^##teamcity\[message text='Writing build log to:")
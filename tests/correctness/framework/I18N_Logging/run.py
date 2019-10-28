from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest
import locale

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
			self.xpybuild(stdouterr=f, args=['-F', f, 'OUTPUT_DIR='+self.output+'/build-output/'+f])

	def validate(self):
		i18n = b'utf8_European\\xe1\\xc1x\\xdf_Katakana\\uff89\\uff81\\uff90\\uff81\\uff7f\\uff78\\uff81\\uff7d\\uff81\\uff7f\\uff76\\uff72\\uff7d\\uff84_Hiragana\\u65e5\\u672c\\u8a9e_Symbols\\u2620\\u2622\\u2603_abc123@#\\xa3!~=\\xa3x'.decode('unicode_escape')
		for f in self.formatters:
			self.assertGrep(f+'.out', expr='TypeError', contains=False)
			self.assertGrep(f+'.out', expr='Traceback', contains=False)

			self.assertGrep(f+'.out', expr='Test message from build file at WARN level', contains=f!='progress')
			self.assertGrep(f+'.out', expr='Test message from build file at INFO level', contains=False)
			
			self.assertGrep(f+'.log', expr='Test message containing I18N chars: %s end'%i18n, encoding='utf-8')
			self.assertGrep(f+'.out', expr='Test message containing I18N chars: .+ end', encoding=locale.getpreferredencoding(), contains=f!='progress')
		
		self.assertGrep('make.out', expr='^Writing build log to') # check there's no weird prefix at beginning of line
		self.assertGrep('make.out', expr='.+test.xpybuild.py:12: error: Test message from build file at ERROR level')
		self.assertGrep('visualstudio.out', expr=r'.+test.xpybuild.py[(]12[)] : error run: Test message from build file at ERROR level')
		
		self.assertGrep('teamcity.out', expr=r"^##teamcity\[message text='Writing build log to:")
		self.assertGrep('teamcity.out', expr=r"^##teamcity\[message text='Test message from build file at ERROR level' status='ERROR'\]")
		self.assertGrep('teamcity.out', expr=r"^##teamcity\[progressMessage '")

from propertysupport import *
from buildcommon import *
from pathsets import *

from targets.writefile import *

defineOutputDirProperty('OUTPUT_DIR', None)

class CustomTarget(WriteFile):
	def run(self, context):
		self.log.warn('Test message containing I18N chars: %s end',  b'utf8_European\\xe1\\xc1x\\xdf_Katakana\\uff89\\uff81\\uff90\\uff81\\uff7f\\uff78\\uff81\\uff7d\\uff81\\uff7f\\uff76\\uff72\\uff7d\\uff84_Hiragana\\u65e5\\u672c\\u8a9e_Symbols\\u2620\\u2622\\u2603_abc123@#\\xa3!~=\\xa3x'.decode('unicode_escape'))
		return super(CustomTarget, self).run(context)

CustomTarget('${OUTPUT_DIR}/output.txt', 'Test message')

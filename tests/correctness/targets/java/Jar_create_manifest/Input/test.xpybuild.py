from xpybuild.buildcommon import enableLegacyXpybuildModuleNames
enableLegacyXpybuildModuleNames() # a useful test to have this enabled; the unusual importing of both utils and targets showed up an extra edge case

from propertysupport import *

from buildcommon import *
from pathsets import *

from utils.java import create_manifest
from targets.java import Jar
from targets.writefile import *
from targets.unpack import *
import logging

def getoutput(context):
	r = []
	r.append('72 bytes per line')

	options = {'jar.manifest.defaults':
		{}
	}
	
	for p in [
			{'a':'xyz'},
			{'a':'x\\t\\nz'}, 
			{'  a ':'   xyz  \t '}, # stripping of whitespace
			{'a':'y'*67},
			{'a':'y'*68},
			{'a':'y'*69},
			{'a':'y'*70},
			
			# whitespace spilling over newline continuation
			{'b':'z'*65+' Z'},
			{'b':'z'*65+'  Z'},
			{'b':'z'*66+'   Z'},
			{'b':'z'*66+'    Z'},

			# default value testing
			{'c':'some value   c'+'c'*70},
			{'c':'some value', 'd':'default value override'},

			{'u':'utf8 string '+'u'*70+b'utf8_European\\xe1\\xc1x\\xdf_Katakana\\uff89\\uff81\\uff90\\uff81\\uff7f\\uff78\\uff81\\uff7d\\uff81\\uff7f\\uff76\\uff72\\uff7d\\uff84_Hiragana\\u65e5\\u672c\\u8a9e_Symbols\\u2620\\u2622\\u2603_abc123@#\\xa3!~=\\xa3x'.decode('unicode_escape')
},

		]:
		r.append('|'+'.'*72+'|') # spec says: No line may be longer than 72 bytes (not characters), in its UTF8-encoded form. assume one \n for newline
		if 'c' in p:
			options['jar.manifest.defaults'] = {'d':'default value '+'d'*70}
		
		r.extend([(b'|'+l.replace(b'\r',b'\\r')+b'|').decode('utf-8') for l in create_manifest(None, p, options).replace(b'\n', b'N\n').split(b'\n')])
		r.append('-----')
	
	r = '\n'.join(r)
	assert isinstance(r, str)
	return r

WriteFile('${OUTPUT_DIR}/output.txt', getoutput, encoding='utf-8')

defineStringProperty('TITLE', 'title')

# also useful to test with the jar target since the jar executable munges it further
Jar('${OUTPUT_DIR}/test.jar', [], [], manifest={
	'Implementation-Title':'My ${TITLE} ',
	' Main-Class ':' my.main ',
	'Header-2':' value 2 ',
	'Header-3':' value 3 '+'x'*150+'_',
 })

Unpack('${OUTPUT_DIR}/unpacked/', '${OUTPUT_DIR}/test.jar')
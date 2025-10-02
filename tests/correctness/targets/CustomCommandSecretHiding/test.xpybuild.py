import os
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.writefile import *
from xpybuild.targets.copy import *
from xpybuild.targets.custom import *

defineOutputDirProperty('OUTPUT_DIR', None)
defineOutputDirProperty('INPUT_DIR', None)

defineStringProperty('MY_PASSWORD', 'hiddentext1')
defineStringProperty('MY_PROPERTY_THAT_CONTAINS_A_PWD', 'prefix-${MY_PASSWORD}')

print (enableEnvironmentPropertyOverrides('XPYTEST_'))
defineStringProperty('MY_CUSTOM_PWD_ENV', '')
defineStringProperty('MY_CUSTOM_PWD_EMPTY_ENV', 'abc')

defineOption('myOption', '${MY_PASSWORD}')

setGlobalOption('common.secretPropertyNamesRegex', '.*(_PASSWORD|_TOKEN|_CREDENTIAL|MY_CUSTOM_PWD).*')
defineStringProperty('MY_CUSTOM_PWD', 'hiddentext2')


env = dict(os.environ)
env['MY_TOKEN_ENV_VAR'] = defineStringProperty('MY_TOKEN_ENV', 'hiddentext3')
CustomCommand('${OUTPUT_DIR}/cmd-output.txt', command=[
	sys.executable,
	'${INPUT_DIR}/testcmd.py',
	'--param1=${MY_PASSWORD}',
	'--param2=${MY_CUSTOM_PWD}',
	'--passwordParam=not-hidden',
	],
	env=env,
	redirectStdOutToTarget=True,
	).option('myOption', '${MY_PASSWORD}')


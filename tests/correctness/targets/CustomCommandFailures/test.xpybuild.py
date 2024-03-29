import os
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.writefile import *
from xpybuild.targets.copy import *
from xpybuild.targets.custom import *

defineOutputDirProperty('OUTPUT_DIR', None)

def makeShellCommand(cmd):
	return [
		os.getenv('ComSpec', 'cmd.exe'), '/c', cmd] if IS_WINDOWS else [
		'/usr/bin/bash', '-c', cmd]
		
CustomCommand('${OUTPUT_DIR}/cmd-output/', commands=[
		makeShellCommand('echo Writing to stdout here'), 
		makeShellCommand('echo Writing to stderr here 1>&2 && exit 123'), # write to stderr
	],
	)


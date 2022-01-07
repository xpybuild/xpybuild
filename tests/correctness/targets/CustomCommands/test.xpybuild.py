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
		makeShellCommand('echo Hello > output.txt'),
		makeShellCommand('echo world >> output.txt'),
		lambda path, deps, context: makeShellCommand('echo Stdout rocks'),
		makeShellCommand('echo All done now!'),
	],
	env=os.environ,
	)


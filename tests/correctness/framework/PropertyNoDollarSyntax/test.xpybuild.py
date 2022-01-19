from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.writefile import *
from xpybuild.targets.copy import *

defineOutputDirProperty('OUTPUT_DIR', None)

defineStringProperty('PROP_FOO', 'foo')
defineStringProperty('PROP_BAR', 'bar')
defineStringProperty('PROP_BOTH', '${PROP_FOO}{PROP_BAR}')

defineOption('myOption', '${PROP_FOO}{PROP_BAR}')

WriteFile('${OUTPUT_DIR}/output-${PROP_FOO}{PROP_BAR}.txt', 'Hello')

WriteFile('${OUTPUT_DIR}/escaping1-$${literal1}.txt', 'Hello')
WriteFile('${OUTPUT_DIR}/escaping2-{{}literal2}.txt', 'Hello')

Copy('${OUTPUT_DIR}/mysrc1/', WriteFile('hello.txt', 'Hello'))
Copy('{OUTPUT_DIR}/mysrc2/', '{OUTPUT_DIR}/hello.txt')
Copy('mydest/', [
	# check that both forms of output dir work
	DirBasedPathSet(DirGeneratedByTarget('${OUTPUT_DIR}/mysrc1/'), 'hello.txt'),
	AddDestPrefix('a/', DirBasedPathSet(DirGeneratedByTarget('{OUTPUT_DIR}/mysrc2/'), 'hello.txt')),
	AddDestPrefix('b/', DirBasedPathSet(DirGeneratedByTarget('${OUTPUT_DIR}/mysrc2/'), 'hello.txt')),
	])


from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.java import *
from xpybuild.targets.copy import *
from xpybuild.targets.archive import *

# xpybuild properties are immutable substitution values 
# which can be overridden on the command line if needed
# (type can be string/path/outputdir/list/enumeration/bool)
defineStringProperty('APP_VERSION', '1.0.0.0')
defineOutputDirProperty('OUTPUT_DIR', 'build-output')
definePathProperty('MY_DEPENDENT_LIBRARY_DIR', './libs', mustExist=True)

Jar('${OUTPUT_DIR}/myapp.jar', 
	# FindPaths walks a directory tree, supporting complex ant-style globbing patterns for include/exclude
	compile=[
		FindPaths('./src/', excludes=['**/VersionConstants.java']), 
		'${BUILD_WORK_DIR}/filtered-java-src/VersionConstants.java',
	],
	
	# DirBasedPathSet statically lists dependent paths under a directory
	classpath=[DirBasedPathSet('${MY_DEPENDENT_LIBRARY_DIR}/', 'mydep-api.jar', 'mydep-core.jar')],
	
	# Specify Jar-specific key/values for the MANIFEST.MF (in addition to any set globally via options)
	manifest={'Implementation-Title':'My Amazing Java Application'}, 
).tags('myapp') # tags make it easy to build a subset of targets on the command line

FilteredCopy('${BUILD_WORK_DIR}/filtered-java-src/VersionConstants.java', './src/VersionConstants.java', 
	StringReplaceLineMapper('@APP_VERSION@', '${APP_VERSION}'),
)

# Global 'options' provide an easy way to apply common settings to all targets; 
# options can be overridden for individual targets using `BaseTarget.option(key,value)`
setGlobalOption('jar.manifest.defaults', {'Implementation-Version': '${APP_VERSION}'})

Zip('${OUTPUT_DIR}/myapp-${APP_VERSION}.zip', [
	'${OUTPUT_DIR}/myapp.jar',
	
	# The xpybuild "PathSet" concept provides a powerful way to specify sets of source paths, 
	# and to map each to a corresponding destination (in this case by adding on a prefix)
	AddDestPrefix('licenses/', FindPaths('./license-files/', includes='**/*.txt'))
])

# In a large build, you'd split your build across multiple files, included like this:
include('subdir/otherbits.xpybuild.py')


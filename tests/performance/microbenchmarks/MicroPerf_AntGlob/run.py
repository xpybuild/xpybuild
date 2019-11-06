from pysys.constants import *
from xpybuild.microperf_basetest import MicroPerfPySysTest


class PySysTest(MicroPerfPySysTest):
	OPERATIONS = [
	# resultKey (must be a valid filename), command, setup
	('antGlobMatch() match',                      "xpybuild.utils.antglob.antGlobMatch('path1/**/*.foo', 'path1/path2/path3/bar.foo')", "import xpybuild.utils.antglob"),
	('antGlobMatch() non-match',                  "xpybuild.utils.antglob.antGlobMatch('path1/**/*.foo', 'path2/path2/path3/bar.foo')", "import xpybuild.utils.antglob"),
	('antGlobMatch() non-match with file/dir mix',"xpybuild.utils.antglob.antGlobMatch('path1/**/*.foo', 'path2/path2/path3/bar.foo/')", "import xpybuild.utils.antglob"),
	('antGlobMatch() double-star wildcard',       "xpybuild.utils.antglob.antGlobMatch('**', 'path2/path2/path3/bar.foo')", "import xpybuild.utils.antglob"), # common, so hopefully optimized
	('antGlobMatch() double-star/path wildcard',  "xpybuild.utils.antglob.antGlobMatch('**/*.foo', 'path2/path2/path3/bar.foo')", "import xpybuild.utils.antglob"), # common, so hopefully optimized

	]
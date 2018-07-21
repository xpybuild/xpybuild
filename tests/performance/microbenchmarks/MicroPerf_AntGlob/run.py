from pysys.constants import *
from xpybuild.microperf_basetest import MicroPerfPySysTest


class PySysTest(MicroPerfPySysTest):
	OPERATIONS = [
	# resultKey (must be a valid filename), command, setup
	('antGlobMatch() match', "utils.antglob.antGlobMatch('path1/**/*.foo', 'path1/path2/path3/bar.foo')", "import utils.antglob"),
	('antGlobMatch() non-match',"utils.antglob.antGlobMatch('path1/**/*.foo', 'path2/path2/path3/bar.foo')", "import utils.antglob"),
	('antGlobMatch() non-match with file/dir mix',"utils.antglob.antGlobMatch('path1/**/*.foo', 'path2/path2/path3/bar.foo/')", "import utils.antglob"),
	('antGlobMatch() double-start wildcard',"utils.antglob.antGlobMatch('**', 'path2/path2/path3/bar.foo')", "import utils.antglob"), # common, so hopefully optimized

	]
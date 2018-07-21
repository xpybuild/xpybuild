from pysys.constants import *
from xpybuild.microperf_basetest import MicroPerfPySysTest


class PySysTest(MicroPerfPySysTest):
	OPERATIONS = [
	# resultKey (must be a valid filename), command, setup
	('toLongPathSafe() noop',"utils.fileutils.toLongPathSafe(OUTPUT_DIR+'/foo%010d0'%0)", ""),
	('toLongPathSafe() using cached data',"utils.fileutils.toLongPathSafe(OUTPUT_DIR+'/foo%010d/'%0)", ""),
	('toLongPathSafe() with no caching',"utils.fileutils.toLongPathSafe(OUTPUT_DIR+'/foo%010d/' % iteration)", ""),
	('toLongPathSafe() dirnormrequired_caching',"utils.fileutils.toLongPathSafe(OUTPUT_DIR+'/foo%010d/../'%0)", ""),
	]
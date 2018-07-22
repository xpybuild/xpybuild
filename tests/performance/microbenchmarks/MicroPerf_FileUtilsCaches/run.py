from pysys.constants import *
from xpybuild.microperf_basetest import MicroPerfPySysTest

class PySysTest(MicroPerfPySysTest):
	OPERATIONS = [
	# resultKey (must be a valid filename), command, setup
	('fileutils.exists() non-existent file without caching',"utils.fileutils.exists(OUTPUT_DIR+'/doesntexist%d'%iteration)", ""),
	('fileutils.exists() non-existent file with caching',"utils.fileutils.exists(OUTPUT_DIR+'/doesntexist')", ""),
	]
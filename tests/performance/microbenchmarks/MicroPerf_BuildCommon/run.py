from pysys.constants import *
from xpybuild.microperf_basetest import MicroPerfPySysTest


class PySysTest(MicroPerfPySysTest):
	OPERATIONS = [
	# resultKey (must be a valid filename), command, setup
	('xpybuild.buildcommon.isDirPath()','isDirPath(OUTPUT_DIR)', ""), 
	('xpybuild.fileutils.isDirPath()','fileutils_isDirPath(OUTPUT_DIR)', "from xpybuild.utils.fileutils import isDirPath as fileutils_isDirPath"),
	
	('isWindows()','isWindows()',''), 
	]
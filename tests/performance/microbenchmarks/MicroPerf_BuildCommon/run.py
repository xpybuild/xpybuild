from pysys.constants import *
from xpybuild.microperf_basetest import MicroPerfPySysTest


class PySysTest(MicroPerfPySysTest):
	OPERATIONS = [
	# resultKey (must be a valid filename), command, setup
	('buildcommon.isDirPath()','isDirPath(OUTPUT_DIR)', ""), 
	('fileutils.isDirPath()','fileutils_isDirPath(OUTPUT_DIR)', "from utils.fileutils import isDirPath as fileutils_isDirPath"),
	
	('isWindows()','isWindows()',''), 
	]
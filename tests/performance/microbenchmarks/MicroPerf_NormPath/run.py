from pysys.constants import *
from xpybuild.microperf_basetest import MicroPerfPySysTest


class PySysTest(MicroPerfPySysTest):
	OPERATIONS = [
	# resultKey (must be a valid filename), command, setup
	('normpath(unique)',"normpath(OUTPUT_DIR+'/'+str(iteration))", ""), 
	# deliberately make it always lowercase the drive letter on windows
	('normLongPath(unique)',"normLongPath(OUTPUT_DIR[0].upper()+OUTPUT_DIR[1:]+'/'+str(iteration))", ""), 
	]
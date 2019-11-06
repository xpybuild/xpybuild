from pysys.constants import *
from xpybuild.microperf_basetest import MicroPerfPySysTest


class PySysTest(MicroPerfPySysTest):
	OPERATIONS = [
	# resultKey (must be a valid filename), command, setup
	('BuildFileLocation constructor','BuildFileLocation()', 'from xpybuild.utils.buildfilelocation import BuildFileLocation'),
	]
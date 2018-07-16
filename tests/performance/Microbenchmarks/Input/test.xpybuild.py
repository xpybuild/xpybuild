import os, logging, time
from propertysupport import *
from buildcommon import *
from pathsets import *
from targets.writefile import WriteFile
from utils.fileutils import isDirPath as fileutils_isDirPath
from utils.buildfilelocation import BuildFileLocation
import utils.fileutils
import utils.antglob

OUTPUT_DIR = getPropertyValue('OUTPUT_DIR')

t = time.time()
ops = 0
while time.time()-t < 3:
	for i in range(10000):
		ops += 1
		@OP@
t = time.time()-t
logging.getLogger('perfreporting').critical('Performed %d operations: %s', ops, """@OP@""")
logging.getLogger('perfreporting').critical('Microbenchmark operation took %f ms each', (1000.0*(t))/ops)

WriteFile('${OUTPUT_DIR}/dummy.txt', '')
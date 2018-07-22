from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest
import io, collections

TEST_PY = u"""
import os, logging, time
from propertysupport import *
from buildcommon import *
from pathsets import *
from targets.writefile import WriteFile
import utils.fileutils
@SETUP@

OUTPUT_DIR = getPropertyValue('OUTPUT_DIR')

t = time.time()
iteration = 0
while time.time()-t < @DURATION_SECS@:
	for i in range(10000):
		iteration += 1
		@OP@
t = time.time()-t
logging.getLogger('perfreporting').critical('Performed %d operations in %f seconds', iteration, t)
logging.getLogger('perfreporting').critical('Microbenchmark operation took %f ns each', (1000.0*1000.0*1000.0*(t))/iteration)

WriteFile('${OUTPUT_DIR}/dummy.txt', '')

"""

class MicroPerfPySysTest(XpybuildBaseTest):
	#OPERATIONS = [ (resultKey (must be a valid filename), command, setup), ... ]

	@staticmethod
	def escapeOpName(opname):
		return re.sub('[^a-zA-Z0-9.-]', '_', opname)
	def execute(self):
		for opname, command, setup in self.OPERATIONS:
			bf = self.output+'/'+self.escapeOpName(opname)+'.xpybuild.py'
			with io.open(bf, 'w') as f:
				f.write(TEST_PY
					.replace('@OP@', command)
					.replace('@SETUP@', setup)
					.replace('@DURATION_SECS@', getattr(self, 'XPYBUILD_MICRO_DURATION_SECS', '3.0')))
			try:
				self.xpybuild(buildfile=bf, shouldFail=False, args=['-n'],stdouterr=self.escapeOpName(opname))
			except Exception as e:
				self.addOutcome(NOTVERIFIED, 'xpybuild failed for %s'%opname, abortOnError=False)

	def validate(self):
		IGNORE_MISSING_PERF_RESULTS = getattr(self, 'IGNORE_MISSING_PERF_RESULTS', '')=='true'
		if IGNORE_MISSING_PERF_RESULTS:
			del self.outcome[:]
		
		for opname, _, _ in self.OPERATIONS:
			try:
				result = float(self.getExprFromFile(self.escapeOpName(opname)+'.out', 'Microbenchmark operation took ([0-9.]+) ns each'))
				self.reportPerformanceResult(result, 
					'Time %s'%opname, 'ns')
				self.log.info('   = {:,} operations/sec'.format(int(1000.0*1000.0*1000.0/result)))
				self.log.info('')
			except Exception as e:
				if IGNORE_MISSING_PERF_RESULTS:
					self.addOutcome(NOTVERIFIED, 'missing output for %s: %s'%(opname, e), abortOnError=False)			
				else:
					raise
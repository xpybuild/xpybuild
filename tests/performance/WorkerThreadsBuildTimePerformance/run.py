import multiprocessing
import random
import time

from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):
	buildRoot = None # can override this with -XbuildRoot=path to measure your own build

	def execute(self):
		buildroot = self.buildRoot if self.buildRoot else self.input
		assert os.path.isdir(buildroot), self.buildroot
	
		cpus = multiprocessing.cpu_count()
		pending = set()
		pending.add(1)
		pending.add(cpus*1//5)
		pending.add(cpus*2//5)
		pending.add(cpus*3//5)
		pending.add(cpus*4//5)
		pending.add(cpus)
		#for i in range(1, (cpus)/4 + 1):
		#	pending.add(i*4)
		#pending.add(1)
		pending = sorted(p for p in pending if p > 0)
		self.log.info('This machine has %d CPUs', cpus)
		self.log.info('Planning to run with workers=%s', pending)

		random.shuffle(pending) # shuffle to reduce impact of caching; also means if we cycle this test we'll get more useful data
		
		self.bestSoFar = 10000000000
		self.bestSoFarWorkers = 1
		self.results = {}
		starttime = time.time()
		
		def runbuild(workers):
			assert workers <= cpus, workers
			assert workers > 0
			self.log.info('(%d/%d) Building with workers=%d (approx %0.1f hours left)', len(self.results)+1, len(pending), workers, 
				-1 if (len(self.results)==0) else ( # avoid div by zero on first one
				(len(pending)-len(self.results) + 2) # number left; add 2 for possible extra runs
				*(time.time()-starttime)/len(self.results) # average time per result
				/60.0/60.0 # secs to hours
				)
			)
			t = time.time()
			#time.sleep(1)
			env = dict(os.environ) if self.buildRoot else None # inherit full parent env for custom builds
			self.xpybuild(args=['--workers', str(workers), 
				'%s=%s'%(getattr(self, 'buildOutputDirProperty', 'OUTPUT_DIR'), self.output+'/output%d'%workers)], buildfile=buildroot+'/root.xpybuild.py', stdouterr='xpybuild-j%d'%workers, timeout=2*60*60, env=env, setOutputDir=False)
			t = time.time()-t
			self.reportPerformanceResult(t, 'Total build time with %d worker threads'%workers, 's', resultDetails={'workers':workers})
			self.results[workers] = t
			if t < self.bestSoFar:
				self.bestSoFar, self.bestSoFarWorkers = t, workers
			self.deletedir(self.output+'/output%d'%workers)
			self.log.info('')
		
		for w in pending:
			runbuild(w)
		
		# explore slightly more or less than the best to find the optimum, even if not in the pending list
		while self.bestSoFarWorkers < cpus and self.bestSoFarWorkers+1 not in self.results:
			self.log.info('Best so far is %d; running an extra test for one extra worker', self.bestSoFarWorkers)
			runbuild(self.bestSoFarWorkers+1)
		while self.bestSoFarWorkers>1 and self.bestSoFarWorkers-1 not in self.results:
			self.log.info('Best so far is %d; running an extra test for one less worker', self.bestSoFarWorkers)
			runbuild(self.bestSoFarWorkers-1)

		for w in sorted(self.results):
			self.log.info('Time for % 2d workers: %0.1f', w, self.results[w])
		self.log.info('')

		self.log.info('Optimum number of workers is %d', self.bestSoFarWorkers)
		self.log.info('... which is a multiplier of %0.2f for this %d CPU machine', self.bestSoFarWorkers/float(cpus), cpus)
		self.log.info('(for a more accurate result, run with multiple cycles and plot the results .csv in a spreadsheet)')


	def validate(self):
		self.addOutcome(PASSED)

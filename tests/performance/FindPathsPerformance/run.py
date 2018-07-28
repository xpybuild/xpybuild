from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest
import shutil

class PySysTest(XpybuildBaseTest):
	NUMBER_PATTERNS = 50
	NUMBER_TARGETS = 5 # this is just to get a more stable number
	NUMBER_FILES = 2000

	def execute(self):
		self.mkdir('findpathsroot/included')
		self.mkdir('findpathsroot/excluded')
		for i in range(self.NUMBER_FILES):
			open(self.output+'/findpathsroot/included/test%d.txt'%i,'w').close()
			open(self.output+'/findpathsroot/excluded/test%d.txt'%i,'w').close()
		
		self.xpybuild(shouldFail=False, args=['-n', 
			'NUMBER_PATTERNS=%s'%self.NUMBER_PATTERNS, 
			'NUMBER_TARGETS=%s'%self.NUMBER_TARGETS, #'--log-level=debug', #'--profile',
			], stdouterr='xpybuild_many')
		self.xpybuild(shouldFail=False, args=['-n', 
			'NUMBER_PATTERNS=1', 
			'NUMBER_TARGETS=%s'%(self.NUMBER_TARGETS*5), 
			], stdouterr='xpybuild_1')
		self.xpybuild(shouldFail=False, args=['-n', 
			'NUMBER_PATTERNS=1', 
			'PATTERN=**', 
			'NUMBER_TARGETS=%s'%(self.NUMBER_TARGETS*10), 
			], stdouterr='xpybuild_starstar')
		self.xpybuild(shouldFail=False, args=['-n', 
			'NUMBER_PATTERNS=1', 
			'PATTERN=**/test*', 
			'NUMBER_TARGETS=%s'%(self.NUMBER_TARGETS*5), 
			], stdouterr='xpybuild_starstar_pattern')
		try:
			shutil.rmtree(self.output+'/findpathsroot')
		except Exception as e:
			self.log.info('Failed to cleanup findpathsroot: %s', e)

	def validate(self):
		self.assertGrep(file='xpybuild_1.out', expr="ERROR .*", contains=False)
		self.assertGrep(file='xpybuild_many.out', expr="ERROR .*", contains=False)
		self.assertGrep(file='xpybuild_starstar.out', expr="ERROR .*", contains=False)
		self.assertGrep(file='xpybuild_starstar_pattern.out', expr="ERROR .*", contains=False)
		
		# try to normalize to get a per-file figure
		# if we're mostly matching then cost is proportional to number of matches, else to number files*pathsets
		def getnormfactor(f):
			matches = sum([int(x) for x in self.getExprFromFile(f, 'FindPaths .*found ([0-9]+) path', returnAll=True)])
			assert matches > 0, f
			nonmatches = (len(self.getExprFromFile(f, 'FindPaths .*found ([0-9]+) path', returnAll=True))*self.NUMBER_FILES)
			assert nonmatches >- 0, f

			self.log.info('matched paths: %s FindPaths instances * numfiles: %s', matches, nonmatches)
			return max(matches, nonmatches)
			
		deps = float(self.getExprFromFile('xpybuild_many.out', 'dependency resolution took ([0-9.]+) s'))
		self.reportPerformanceResult(1000*1000*1000*deps/getnormfactor('xpybuild_many.log'), 'PathSet FindPaths resolution time per file with %d include patterns'%self.NUMBER_PATTERNS, 'ns')

		deps = float(self.getExprFromFile('xpybuild_1.out', 'dependency resolution took ([0-9.]+) s'))
		self.reportPerformanceResult(1000*1000*1000*deps/getnormfactor('xpybuild_1.log'), 'PathSet FindPaths resolution time per file with 1 include pattern', 'ns')

		deps = float(self.getExprFromFile('xpybuild_starstar.out', 'dependency resolution took ([0-9.]+) s'))
		self.reportPerformanceResult(1000*1000*1000*deps/getnormfactor('xpybuild_starstar.log'), 'PathSet FindPaths resolution time per file with ** include pattern', 'ns')

		deps = float(self.getExprFromFile('xpybuild_starstar_pattern.out', 'dependency resolution took ([0-9.]+) s'))
		self.reportPerformanceResult(1000*1000*1000*deps/getnormfactor('xpybuild_starstar_pattern.log'), 'PathSet FindPaths resolution time per file with **/test* pattern', 'ns')

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
		try:
			shutil.rmtree(self.output+'/findpathsroot')
		except Exception as e:
			self.log.info('Failed to cleanup findpathsroot: %s', e)

	def validate(self):
		self.assertGrep(file='xpybuild_1.out', expr="ERROR .*", contains=False)
		self.assertGrep(file='xpybuild_many.out', expr="ERROR .*", contains=False)
		
		deps = float(self.getExprFromFile('xpybuild_many.out', 'dependency resolution took ([0-9.]+) s'))
		self.reportPerformanceResult(1000*deps/self.NUMBER_TARGETS/self.NUMBER_FILES, 'PathSet FindPaths resolution time per file with %d include patterns'%self.NUMBER_PATTERNS, 'ms')

		deps = float(self.getExprFromFile('xpybuild_1.out', 'dependency resolution took ([0-9.]+) s'))
		self.reportPerformanceResult(1000*deps/(self.NUMBER_TARGETS*5)/self.NUMBER_FILES, 'PathSet FindPaths resolution time per file with 1 include pattern', 'ms')

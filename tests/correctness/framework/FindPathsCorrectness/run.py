from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest
import shutil, re

class PySysTest(XpybuildBaseTest):
	NUMBER_PATTERNS = 50
	NUMBER_TARGETS = 5 # this is just to get a more stable number
	NUMBER_FILES = 2000

	def execute(self):
		for a in ['1', '2', '3']:
			for b in ['a', 'b', 'c']:
				for c in ['xix', 'xiix', 'xiiix']:
					self.mkdir('findpathsroot/'+a+'/'+b+'/'+c+'D')
					open(self.output+'/findpathsroot/'+a+'/'+b+'/'+c, 'wb').close()
					
					# need a file more path elements than some of our expressions
					open(self.output+'/findpathsroot/1/a/xixD/somefile', 'wb').close()
					
		self.xpybuild(args=[])
		try:
			shutil.rmtree(self.output+'/findpathsroot')
		except Exception as e:
			self.log.info('Failed to cleanup findpathsroot: %s', e)

	def validate(self):
		for i in range(5):
			i += 1
			x = self.output+'/build-output/target%d'%(i)
			paths = []
			for (dirpath, dirnames, filenames) in os.walk(x):
				for p in filenames: paths.append((dirpath[len(x):].replace('\\','/')+'/'+p).lstrip('/'))
				for p in dirnames: paths.append((dirpath[len(x):].replace('\\','/')+'/'+p+'/').lstrip('/'))
			with open(self.output+'/target%d.txt'%i, 'w') as f:
				f.write('\n'.join(sorted(paths)))
			self.logFileContents('target%d.txt'%i, maxLines=0)
			
			self.assertDiff('target%d.txt'%i, 'target%d.txt'%i, abortOnError=False)
		
		self.assertGrep(file='xpybuild.out', expr=re.escape('Invalid pattern (pattern elements containing "**" must not have any other characters): a/**b**/c'))

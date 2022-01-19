from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest
import shutil, re

class PySysTest(XpybuildBaseTest):
	def execute(self):
		self.mkdir('input/mydir/exclude-dir')
		self.mkdir('input/mydir/included')
		for f in [
				'input/mydir/included/file.txt',
				'input/mydir/exclude-dir/file.txt',
				'input/mydir/exclude-file',
				'input/mydir/.nfs1234',
		]:
			self.write_text(f, 'x')

		self.xpybuild(args=['CUSTOM_GLOBAL_EXCLUDES=True', 'OUTPUT_DIR=%s/custom'%self.output], stdouterr='xpybuild-custom')
		self.xpybuild(args=['OUTPUT_DIR=%s/default'%self.output], stdouterr='xpybuild-default')

	def validate(self):
		for i in ['custom', 'default']:
			x = self.output+'/'+i
			paths = []
			for (dirpath, dirnames, filenames) in os.walk(x):
				if 'BUILD_WORK' in dirnames: dirnames.remove('BUILD_WORK')
				for p in filenames: paths.append((dirpath[len(x):].replace('\\','/')+'/'+p).lstrip('/'))
				for p in dirnames: paths.append((dirpath[len(x):].replace('\\','/')+'/'+p+'/').lstrip('/'))
			with open(self.output+'/'+i+'.txt', 'w') as f:
				f.write('\n'.join(sorted(paths)))
			self.logFileContents(i+'.txt', maxLines=0)
			
			self.assertDiff(i+'.txt')

import shutil 
from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		if not hasattr(os, 'symlink'): self.skipTest('this OS does not support symlinks')
		self.mkdir('symlink-relative/foo/')
		self.mkdir('symlink-relative/foo/subdir/')
		self.mkdir('symlink-absolute/foo/subdir/')
		with open(self.output+'/symlink-relative/foo/subdir/sourcefile.txt', 'wb') as f:
			f.write(b'Hello world')
		with open(self.output+'/symlink-absolute/foo/subdir/sourcefile.txt', 'wb') as f:
			f.write(b'Hello world')
		# source, linkname
		os.symlink(self.output+'/symlink-absolute/foo/subdir/sourcefile.txt',
			self.output+'/symlink-absolute/foo/subdir/mylink.txt')
		os.symlink(self.output+'/symlink-absolute/foo/subdir', 
			self.output+'/symlink-absolute/foo/subdir-link')

		os.symlink('../subdir/sourcefile.txt',
			self.output+'/symlink-relative/foo/subdir/mylink.txt')
		os.symlink('./subdir', 
			self.output+'/symlink-relative/foo/subdir-link')
		
		# the directories aren't working at present

		self.xpybuild(args=['TEST_SYMLINK=tRue', 'OUTPUT_DIR=%s/build-output/symlink'%self.output], stdouterr='xpy-symlink')
		self.xpybuild(args=['TEST_SYMLINK=False', 'OUTPUT_DIR=%s/build-output/no-symlink'%self.output], stdouterr='xpy-no-symlink')

	def validate(self):
		with open(self.output+'/dirlist.txt', 'w') as f:
			def pathtostr(p):
				p = p.replace('\\','/')

				if os.path.islink(p):
					target = os.readlink(p)
					assert os.path.exists(os.path.join(os.path.dirname(p), target)), [p, target]
					if os.path.isdir(p): os.listdir(p) # check we can follow directory links
					if os.path.isdir(p): p +='/'
					p += ' is %s link'%('ABSOLUTE' if os.path.isabs(target) else 'RELATIVE')
					p += ' -> %s'%(target if not os.path.isabs(target) else 'output/'+target[len(self.output)+1:]).replace('\\','/')
				else:
					if os.path.isdir(p): p +='/'

				return p[len(self.output)+1:]+'\n'
			for x in ['symlink', 'no-symlink']:
				for y in ['symlink-absolute', 'symlink-relative']:
					f.write(pathtostr(self.output+'/build-output/'+x+'/'+y+'/foo/subdir/sourcefile.txt'))
					f.write(pathtostr(self.output+'/build-output/'+x+'/'+y+'/foo/subdir/mylink.txt'))
					f.write(pathtostr(self.output+'/build-output/'+x+'/'+y+'/foo/subdir-link'))

		self.logFileContents('dirlist.txt', maxLines=0)
		self.assertDiff('dirlist.txt', 'ref-dirlist.txt')

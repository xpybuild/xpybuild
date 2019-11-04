from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		dirs = list()
		EXCLUDED_MODULES = []

		i = 0
		skipped = 0
		failedModules = []
		
		DIR = PROJECT.XPYBUILD_ROOT
		allScripts = []
		for dirpath, dirnames, filenames in os.walk(DIR):
			for excl in ['.svn', 'tests', 'release-output', 
					# doesn't contain any
					'targets']:
				if excl in dirnames: dirnames.remove(excl)

			for f in filenames:
				if f.endswith('.py') and f != '__init__.py' and f != 'root.xpybuild.py':
					with open(dirpath+'/'+f) as pyfile:
						if '>>>' in pyfile.read():
							if getattr(self, 'DOCTEST_FILTER', '') and self.DOCTEST_FILTER.replace('.py','') != f.replace('.py',''): continue
							
							allScripts.append(dirpath+'/'+f)
		
		good = bad = 0
		for f in allScripts:
			i += 1
			moduleName = f.replace(DIR,'').replace('/','.').replace('\\','.').strip('.').replace('.py','')
			
			if any([re.search(x, moduleName) for x in EXCLUDED_MODULES]):
				self.log.info("skipping excluded module %s"%moduleName)
				skipped += 1
				continue
			
			environs = self.createEnvirons({'PYTHONPATH':DIR+os.pathsep+DIR+'/xpybuild'}, command=sys.executable)
			args = ['-m', 'doctest', '-v', f]
			pythoncoverage = getattr(self, 'pythonCoverage', False)
			if pythoncoverage:
				self.log.info('Enabling Python code coverage')
				# use -a to aggregate the coverage together rather than overwriting
				args = ['-m', 'coverage', 'run', '-a', '--source=%s'%PROJECT.XPYBUILD_ROOT]+args
			result = self.startProcess(sys.executable, args, 
				environs=environs, 
				stdout=moduleName+'.out', stderr=moduleName+'.err', displayName='doctest '+moduleName, 
				abortOnError=True, ignoreExitStatus=True)

			if getattr(self, 'pythonDoctestCoverageReport', False):
				self.startProcess(sys.executable, ['-m', 'coverage', 'html'], 
				environs=environs, 
				stdout='python-coverage.out', stderr='python-coverage.err', displayName='python coverage', 
				abortOnError=True, ignoreExitStatus=False)
				self.log.info('See %s'%os.path.normpath(self.output+'/htmlcov'))


			if result.exitStatus != 0: 
				self.logFileContents(moduleName+'.err', maxLines=0) or self.logFileContents(moduleName+'.out', maxLines=0)
				self.addOutcome(FAILED, 'doctest %s failed'%moduleName, abortOnError=False)
				bad += 1
			else:
				good += 1
			#return # TODO - remove
		assert good+bad > 0, 'some tests should have run'
		self.log.info('Completed doctesting %d modules; %d failed', good+bad, bad)
		self.log.info("%d modules were skipped" % skipped)
		
	def validate(self):
		pass
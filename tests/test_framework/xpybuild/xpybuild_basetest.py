from pysys.constants import *
from pysys.basetest import BaseTest
from pysys.utils.filegrep import filegrep

class XpybuildBaseTest(BaseTest):
	def xpybuild(self, args=None, buildfile='test.xpybuild.py', shouldFail=False, stdouterr='xpybuild', env=None, setOutputDir=True, **kwargs):
		"""
		Runs xpybuild against the specified buildfile or test.xpybuild.py from the 
		input dir. Produces output in the <testoutput>/build-output folder. 
		
		@param shouldFail: by default, the test will abort if the build fails. 
		Set this to True if the build is expected to fail in which case 
		the test will abort if it succeeds, and this method will return a 
		string identifying the target or overall failure message if not. 
		
		@returns the failure message string if shouldFail=True, otherwise nothing
		"""
		
		if 'performance' in self.descriptor.groups: self.disableCoverage = True
		
		stdout,stderr=self.allocateUniqueStdOutErr(stdouterr)
		args = args or []
		try:
			try:
				environs = self.createEnvirons(env, command=sys.executable)
				environs['COVERAGE_FILE'] = '.coverage.%s'%stdouterr # use unique names to avoid overwriting
				environs['PYSYS_TEST_ROOT_DIR'] = self.project.testRootDir
				
				# need to inherit parent PATH so we can find Java
				environs['PATH'] = environs['PATH']+os.pathsep+os.getenv('PATH', '')
				
				newargs = 	[
#					PROJECT.rootdir+'/../xpybuild.py', 
					os.path.normpath(PROJECT.XPYBUILD),
					'-f', os.path.join(self.input, buildfile), 
					'--logfile', os.path.join(self.output, stdout.replace('.out', '')+'.log'), 
					'-J', # might as well run in parallel to speed things up and help find race conditions
					]
				if setOutputDir: newargs.append('OUTPUT_DIR=%s'%self.output+'/build-output')
				args = newargs+args
				pythoncoverage =  getattr(self, 'pythonCoverage', False)
				if pythoncoverage:
					self.log.info('Enabling Python code coverage')
					args = ['-m', 'coverage', 'run', '--source=%s'%PROJECT.XPYBUILD_ROOT, '--omit=*tests/*']+args
				elif os.getenv('XPYBUILD_PPROFILE',None):
					# unfortunately CProfile isn't much use in a multithreaded application, so use pprofile
					self.log.info('Enabling Python per-line pprofile')
					
					profileargs = os.environ['XPYBUILD_PPROFILE']
					if profileargs == 'true':
						profileargs = ['-m', 'pprofile'] # assume it's installed
					else:
						profileargs = [profileargs] # run it as a script
						assert args[0].endswith('py'), args[0] # must be the .py script path not the dir
						assert os.path.isfile(args[0]), args[0]

					if os.getenv('XPYBUILD_PPROFILE_CALLGRIND','')=='true' or getattr(self, 'pprofileCallgrind',False):
						pprof_output = f'callgrind.pprofile.{stdouterr}'
						profileargs.extend(['--format', 'callgrind'])
					else:
						pprof_output = f'pprofile.{stdouterr}.py'
					
					args = profileargs+['--out', pprof_output, 
						#'--include', os.getenv('XPYBUILD_PPROFILE_REGEX', '.*xpybuild.*'), '--exclude', '.*', #'--verbose'
						]+args
					self.log.info('   see %s', os.path.normpath(self.output+'/'+pprof_output))

				result = self.startProcess(sys.executable, args, 
					environs=environs, 
					stdout=stdout, stderr=stderr, displayName=('xpybuild %s'%' '.join(args)).strip(), 
					abortOnError=True, ignoreExitStatus=shouldFail, **kwargs)
				if shouldFail and result != 0: raise Exception('Build failed as expected')
				if getattr(self, 'PYTHON_COVERAGE_REPORT', '')=='true':
					self.startProcess(sys.executable, ['-m', 'coverage', 'html'], 
					environs=environs, 
					stdout='python-coverage.out', stderr='python-coverage.err', displayName='python coverage', 
					abortOnError=True, ignoreExitStatus=False)
					self.log.info('See %s'%os.path.normpath(self.output+'/htmlcov'))

			finally:
				self.logFileContents(stdout, tail=True) or self.logFileContents(stderr, tail=True)
		
		except AssertionError as e:
			self.log.exception('Assertion error: ')
			raise
		except Exception as e:
			m = None
			try:
				# these give the best messages
				m = filegrep(stdout, '(Target FAILED: .*)', returnMatch=True)
				if not m: m = filegrep(stdout, '(XPYBUILD FAILED: .*)', returnMatch=True)
				if m: m = m.group(1)
			except Exception as e2:
				if shouldFail: raise e2 # this is fatal if we need the error message
				self.log.exception('Error handling block failed: ')
			if not m: self.log.warning('Caught exception running build: %s', e)
			m = m or '<unknown failure>'

			if shouldFail: 
				self.log.info('Build failed as expected; message is: %s', m)
				return m
			else:
				self.abort(BLOCKED, 'Build %s failed unexpectedly: %s'%(stdouterr, m))
		else:
			if shouldFail:
				self.abort(FAILED, 'build %s was expected to fail but succeeded'%stdouterr)
		
		return None

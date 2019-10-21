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
					PROJECT.XPYBUILD,
					'-f', os.path.join(self.input, buildfile), 
					'--logfile', os.path.join(self.output, stdout.replace('.out', '')+'.log'), 
					'-J', # might as well run in parallel to speed things up and help find race conditions
					]
				if setOutputDir: newargs.append('OUTPUT_DIR=%s'%self.output+'/build-output')
				args = newargs+args
				pythoncoverage = getattr(self, 'PYTHON_COVERAGE', '')=='true'
				if pythoncoverage:
					self.log.info('Enabling Python code coverage')
					args = ['-m', 'coverage', 'run', '--source=%s'%PROJECT.XPYBUILD_ROOT, '--omit=*tests/*']+args
				elif os.getenv('XPYBUILD_PPROFILE',None):
					self.log.info('Enabling Python per-line pprofile')
					args = [os.environ['XPYBUILD_PPROFILE'], '--out', 'profileoutput.py', 
						'--include', os.getenv('XPYBUILD_PPROFILE_REGEX', '.*xpybuild.*'), '--exclude', '.*', #'--verbose'
						]+args
					assert args[0].endswith('py'), args[0] # use the script path not the dir
					assert os.path.exists(args[0]), args[0]
					self.log.info('   see %s', os.path.normpath(self.output+'/profileoutput.py'))

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
			except Exception, e2:
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

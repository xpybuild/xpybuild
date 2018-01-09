from pysys.constants import *
from pysys.basetest import BaseTest
from pysys.utils.filegrep import filegrep

class XpybuildBaseTest(BaseTest):
	def xpybuild(self, args=None, buildfile='test.xpybuild.py', shouldFail=False):
		"""
		Runs xpybuild against the specified buildfile or test.xpybuild.py from the 
		input dir. Produces output in the <testoutput>/build-output folder. 
		
		@param shouldFail: by default, the test will abort if the build fails. 
		Set this to True if the build is expected to fail in which case 
		the test will abort if it succeeds, and this method will return a 
		string identifying the target or overall failure message if not. 
		
		@returns the failure message string if shouldFail=True, otherwise nothing
		"""
		stdout,stderr=self.allocateUniqueStdOutErr('xpybuild')
		args = args or []
		try:
			try:
				result = self.startProcess(sys.executable, [
					PROJECT.rootdir+'/../xpybuild.py', 
					'-f', os.path.join(self.input, buildfile), 
					'--logfile', os.path.join(self.output, stdout.replace('.out', '')+'.log'), 
					'-J', # might as well run in parallel to speed things up and help find race conditions
					'OUTPUT_DIR=%s'%self.output+'/build-output']+args, 
					# python doesn't seem to launch on linux without PYTHONHOME being set
					environs={'PYTHONHOME':os.path.dirname(os.path.dirname(sys.executable)), 'PYTHONPATH':''}, 
					stdout=stdout, stderr=stderr, displayName=('xpybuild %s'%' '.join(args)).strip(), 
					abortOnError=True, ignoreExitStatus=shouldFail)
				if shouldFail and result != 0: raise Exception('Build failed as expected')
			finally:
				self.logFileContents(stdout, tail=True) or self.logFileContents(stderr, tail=True)
		
		except Exception, e:
			m = None
			try:
				# these give the best messages
				m = filegrep(stdout, '(Target FAILED: .*)', returnMatch=True)
				if not m: m = filegrep(stdout, '(XPYBUILD FAILED: .*)', returnMatch=True)
				if m: m = m.group(1)
			except Exception, e2:
				if shouldFail: raise e2 # this is fatal if we need the error message
				self.log.exception('Error handling block failed: ')
			if not m: log.warning('Caught exception running build: %s', e)
			m = m or '<unknown failure>'

			if shouldFail: 
				self.log.info('Build failed as expected; message is: %s', m)
				return m
			else:
				self.abort(BLOCKED, 'Build failed unexpectedly: %s'%m)
		else:
			if shouldFail:
				self.abort(FAILED, 'build was expected to fail but succeeded')
		
		return None

# xpyBuild - eXtensible Python-based Build System
#
# Copyright (c) 2013 - 2019 Software AG, Darmstadt, Germany and/or its licensors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# $Id: process.py 301527 2017-02-06 15:31:43Z matj $
# Requires: Python 2.6
#

import subprocess, os, time
from threading import Lock
import threading

from xpybuild.buildcommon import *
from xpybuild.utils.outputhandler import ProcessOutputHandler
from xpybuild.utils.buildexceptions import BuildException
from xpybuild.propertysupport import defineOption

import logging
log = logging.getLogger('process')

class __ProcessMonitor(object):
	def __init__(self):
		self._global_process_list = set()
		self._global_process_lock = Lock()
	
	def killall(self):
		with self._global_process_lock:
			log.info('Cleaning up %d remaining child processes: %s', len(self._global_process_list), self._global_process_list)
			for p in self._global_process_list:
				try:
					p.kill()
				except Exception as e:
					if p.poll() == None:
						log.warn('Failed to clean up child process %s: %s', p, e)
			if self._global_process_list:
				log.info('Done cleanup up child processes')
			self._global_process_list.clear()
	def add(self,process):
		with self._global_process_lock:
			self._global_process_list.add(process)
	def remove(self,process):
		with self._global_process_lock:
			try:
				self._global_process_list.remove(process)
			except KeyError:
				pass # during Ctrl+C this can be called more than once

# used by threadpool to force cleanup of children during shutdown
_processCleanupMonitor = __ProcessMonitor()

def _wait_with_timeout(process, displayName, timeout, read):
	"""
	PRIVATE method - do not call
	"""
	# read output from the command, with a timeout
	# returns (out, err, timedout) if read else returncode; out/err are byte buffers
	
	_processCleanupMonitor.add(process)
	timedOut = [False]
	
	parentThreadName = threading.currentThread().name
	
	def kill_proc(): # executed on a background thread
		try:
			threading.currentThread().name = parentThreadName+'-timer'
			log.info('Process timeout handler for %s invoked after %s s; still running=%s', displayName, timeout, process.poll()==None)
			if process.poll()!=None: return # has terminated, so nothing to do - this happen on loaded machines sometimes
			
			# this will cause us to throw an exception
			timedOut[0] = True
			try:
				process.kill()
				log.info('Process kill completed successfully for %s'%displayName)
			except Exception as e:
				# only log if process is still running (Windows Access Denied 5 are seen occasionally in kill()) - should not happen
				time.sleep(2)
				if process.poll() == None:
					log.error('Failed to kill process %s (pid %s) after %d second timeout: %s', displayName, process.pid, timeout, e)
				else:
					log.debug('Process kill failed but process is now stopped anyway: %s', e)
		except Exception as e: # should never happen but make sure we notice if it does
			log.exception('Unexpected error in process timeout monitoring thread for %s: '%displayName)
			
	timer = threading.Timer(timeout, kill_proc, [])
	timer.start()
	try:
		if read:
			stdout, stderr = process.communicate()
		else:
			rv = process.wait()
	finally:
		timer.cancel()
		_processCleanupMonitor.remove(process)
		
	if timedOut[0]:
		if read:
			return stdout, stderr, True
		else:
			raise BuildException('Terminating process %s after hitting %d second timout' % (displayName, timeout))
	else:
		if read:
			return stdout, stderr, False
		else:
			return rv

from xpybuild.internal import DEFAULT_PROCESS_ENCODING as __DEFAULT_PROCESS_ENCODING
def defaultProcessOutputEncodingDecider(context, executable, **forfutureuse):
	"""
	Function providing the default implementation of the ``common.processOutputEncodingDecider``
	option, which determines what encoding to use for parsing output from subprocesses. 
	
	The default implementation ignores the executable argument and returns the same 
	encoding used by the xpybuild process itself (typically the sys.stdout or system default locale).
	
	A custom function can be provided for this option, using the same signature. 
	
	@param context: The current `BuildContext`, which can be used to expand properties. 
	For some targets this may not be set (i.e. None). 
	@param executable: The full absolute path of the executable producing the output. 
	@param forfutureuse: Pass through any additional keyword arguments using ``**forfutureuse``. 
	"""
	return __DEFAULT_PROCESS_ENCODING # stdout encoding will be None unless in a terminal

def call(args, env=None, cwd=None, outputHandler=None, outputEncoding=None, timeout=None, displayName=None, options=None):
	"""
	Call a process with the specified args, logging stderr and stdout to the specified 
	output handler which will throw an exception if the exit code or output 
	of the process indicates an error. 
	
	NB: Consider using the CustomCommand target instead of invoking this directly whenever possible.
	
	@param args: The command and arguments to invoke (a list, the first element of which is the executable). 
		None items in this list will be ignored. 

	@param outputHandler: a ProcessOutputHandler instance, perhaps constructed using 
	the L{ProcessOutputHandler.create} method. If not specified, a default is created 
	based on the supplied options. 

	@param env: Override the environment the process is started in (defaults to the parent environment)

	@param cwd: Change the working directory the process is started in (defaults to the parent cwd)
	
	@param outputEncoding: name of the character encoding the process generates. If specified, 
		this overrides the ``common.processOutputEncodingDecider`` option value (see `defaultProcessOutputEncodingDecider`). 

	@param timeout: maximum time a process is allowed to run. If an options dictionary is not 
	present, this should ALWAYS be set to a value e.g. options['process.timeout']. 
	
	@param displayName: human-friendly description of the process for use in error messages, including the target name if possible=
	
	@param options: where possible, always pass in a dictionary of resolved options, which may be used to customize 
	how this function operates. 
	"""
	if options is None: options = {}
	if not timeout: timeout = options.get('process.timeout', 600)
	
	processName = os.path.basename(args[0])
	#if not timeout: # too many things don't set it at present
	#	raise Exception('Invalid argument to %s call - timeout must always be set explicitly'%processName)

	args = [x for x in args if x != None]

	environs = os.environ.copy()
	if env:
		for k in env:
			if None == env[k]:
				del environs[k]
			else:
				environs[k] = env[k]
	if not cwd: cwd = os.getcwd()
	
	log.info('Executing %s process: %s', processName, ' '.join(['"%s"'%s if ' ' in s else s for s in args]))
	if cwd != os.getcwd():
		log.info('%s working directory: %s', processName, cwd)
	if env: 
		log.info('%s environment overrides: %s', processName, ', '.join(sorted(['%s=%s'%(k, env[k]) for k in env])))
	try:
		if cwd:
			process = subprocess.Popen(args, env=environs, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
		else:
			process = subprocess.Popen(args, env=environs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	except Exception as e:
		raise EnvironmentError('Cannot start process "%s": %s'%(args[0], e))

	if not outputHandler: # use short processName not longer displayName for per-line prefixes, the extra context isn't necessary anyway
		outputHandler = ProcessOutputHandler.create(processName, options=options)

	# give the full arguments as the process display name (unless really long) since it's impossible to identify the target otherwise
	if not displayName:
		displayName = str(args)
		if len(displayName)>200: displayName=displayName[:200]+'...]'
	(out, err, timedout) = _wait_with_timeout(process, displayName, timeout, True)
	
	if outputEncoding is None:
		decider = options.get('common.processOutputEncodingDecider', None) or defaultProcessOutputEncodingDecider
		outputEncoding = decider(context=None, executable=args[0])
	log.debug('%s outputEncoding assumed to be: %s', processName, outputEncoding)
	
	# convert byte buffers to strings	
	# probably best to be tolerant about unexpected chars, given how hard it is to predict what subprocesses will write in 
	out = str(out, outputEncoding, errors='replace')
	err = str(err, outputEncoding, errors='replace')
	
	hasfailed = True
	try:
		for l in out.splitlines():
			outputHandler.handleLine(l, False)
		for l in err.splitlines():
			outputHandler.handleLine(l, True)
			
		if timedout: # only throw after we've written the stdout/err
			raise BuildException('Terminating process %s after hitting %d second timout' % (processName, timeout))
			
		outputHandler.handleEnd(process.returncode) # will throw on error
		hasfailed = False
		return outputHandler
	finally:
		# easy-read format
		if hasfailed:
			log.debug('Arguments of failed process are: %s' % '\n   '.join(['"%s"'%s if ' ' in s else s for s in args]))

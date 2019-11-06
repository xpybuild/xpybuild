# xpyBuild - eXtensible Python-based Build System
#
# This class is responsible for working out what tasks need to run, and for 
# scheduling them
#
# Copyright (c) 2013 - 2018 Software AG, Darmstadt, Germany and/or its licensors
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
# $Id: threadpool.py 301527 2017-02-06 15:31:43Z matj $
#

import traceback, os, signal, threading, time, math, cProfile
import pstats
from threading import Lock, Condition

from xpybuild.basetarget import BaseTarget
from xpybuild.buildcommon import *
from xpybuild.utils.process import _processCleanupMonitor
from xpybuild.utils.fileutils import mkdir

import logging
log = logging.getLogger('xpybuild.scheduler')

class _UtilisationDummy(object):
	""" Dummy class that doesn't log utilisation """
	def __init__(self, max=0):
		pass
	def incr(self):
		pass
	def decr(self):
		pass
	def logSampleStats(self, log):
		pass

class Utilisation(object):
	""" Stat collector for how many threads are in use at any time """
	def __init__(self, max):
		self.max = max
		self.samples=[]
		self.count = 0
		self.lock = Lock()
		self.starttime = time.time()
		self.startsample = None
	def incr(self):
		with self.lock:
			now = time.time()
			if self.startsample:
				self.samples.append((self.count, now-self.startsample))
			self.startsample = now
			self.count = self.count+1
	def decr(self):
		with self.lock:
			now = time.time()
			if self.startsample:
				self.samples.append((self.count, now-self.startsample))
			self.startsample = now
			self.count = self.count-1
	def logSampleStats(self, log):
		with self.lock:
			totalTime = time.time()-self.starttime
			totalUtil = 0
			util = {}
			for (count, elapsed) in self.samples:
				utiltot = util.get(count, 0)
				utiltot = utiltot + elapsed
				util[count] = utiltot
				totalUtil = totalUtil + (count*elapsed)
			log.critical("Utilisation average: %05.2f/%d" % (totalUtil/totalTime, self.max))
			log.critical("Utilisation histogram:")
			for i in range(1, self.max+1):
				log.critical("  [%2d] (%05.2f%%) %s" % (i, 100*(util.get(i, 0)/totalTime), self.bar(util.get(i, 0), totalTime)))
	def bar(self, n, total):
		WIDTH=70
		val = (n/total) * WIDTH
		length = int(round(val))
		return "".join([ '=' for x in range(0, length)])
			

class ThreadPool(object):
	"""
		Thread pool to have a number of workers over a job queue.
		Workers can add more jobs to the queue as they complete.
	"""
	workers = 0
	queue = None
	fn = None
	lock = None
	condition = None
	workerCount = 0
	running = True
	_errors = None
	completed = 0
	inprogress = None
	utilisation = None
	profile = False
	def __init__(self, name, workers, queue, fn, utillogger=None, profile=False):
		"""
			workers - number of workers to start
			queue - queue to pull jobs from (any type)
			fn - function to call to process a job. Signature of that function is fn(queue-item) returns ([new items], [error strings], bool)
			     the boolean should be false if the build run should be aborted
		"""
		self.name = name
		log.debug('Creating thread pool %s with workers=%d; initial queue length is %d', name, workers, queue.qsize())
		self.workers = workers
		self.utilisation = utillogger or _UtilisationDummy()
		self.queue = queue
		self.fn = fn
		self.lock = Lock()
		self.condition = Condition(self.lock)
		self.inprogress = set()
		self.completed = 0
		self._errors = []
		self.__threads = []
		self.profile = profile
		self.threadProfiles = []
	def __getattr__(self, name):
		"""
			errors is a read-only attribute that contains the list of errors returned by the jobs
		"""
		if name == 'errors': return self._errors
		raise AttributeError('Unknown attribute %s'%name)
	def stop(self):
		"""
			Stop running more jobs and stop all the threads
		"""
		log.debug("Stopping thread pool")
		with self.lock:
			self.running = False
			_processCleanupMonitor.killall()
			self.condition.notifyAll()
			signal.signal(signal.SIGINT, self.oldhandler)
	def start(self):
		"""
			Start all the workers and start them running jobs.
			Sets a SIGINT handler to stop all the jobs on ctrl-c
		"""
		log.debug("Starting %s workers, %d in queue", self.workers, self.queue.qsize())
		self.oldhandler = signal.getsignal(signal.SIGINT)
		signal.signal(signal.SIGINT, lambda num, frame: self.stop())
		for i in range(0, self.workers):
			t = threading.Thread(target=lambda: self._worker_main(), name="B-%02d"%(i+1))
			t.start()
			self.__threads.append(t)
	def wait(self):
		"""
			Wait for all the jobs to complete with an empty queue
		"""
		with self.lock:
			wait_time = 15.0
			while self.workerCount > 0 or (self.running and not self.queue.empty()): 
				self.completed=0
				self.condition.wait(wait_time)
				if self.completed == 0:
					log.critical(("*** %d job%s in progress: "+" ".join([str(x) for x in self.inprogress])) % (len(self.inprogress), "" if 1==len(self.inprogress) else "s" ))
					wait_time = 60.0
				else:
					wait_time = 15.0
			if not self.running: 
				log.info('Build aborted')
				if not self._errors:
					self._errors.append("Build aborted")
			
			# before this point running=False means we called stop and aborted it... from now on we use running=False 
			# to terminate the remaining workers before starting the next phase
			self.running = False
			self.condition.notifyAll()
			
		if self.profile: 
			log.debug('Joining threads before aggregating profile info')
			# don't need to bother joining normally, but do for getting profile output
			for t in self.__threads:
				t.join()
			log.debug('Building profile output from %d: %s', len(self.threadProfiles), self.threadProfiles)
			assert self.threadProfiles
			path = 'xpybuild-profile-%s.txt'%self.name
			with open(path, 'w') as f:
				p = pstats.Stats(*self.threadProfiles, stream=f)
				p.sort_stats('cumtime').print_stats(f)
				p.dump_stats(path.replace('.txt', '')) # also in binary format
			
			log.critical('=== Wrote Python profiling output from %d threads to: %s', len(self.threadProfiles), path)
			
	def _worker_main(self):
		"""
			The entry point of the worker threads.
			Loops while the pool is active, waiting for the queue to become non-empty.
			Also takes the returned errors and new queue items and adds them to the appropriate queues
		"""
		log.debug("Starting worker in %s thread pool", self.name)
		if self.profile:
			profiler = cProfile.Profile()
			profiler.enable()
		try:
			while self.running:
				target = None
				# With the lock held wait for a non-empty queue and get an item from it
				with self.lock:
					#log.debug("Checking queue contents")
					while self.queue.empty():
						if self.running:
							#log.debug("Wait for queue to become full")
							self.condition.wait()
						else:
							return
					if not self.running: return
					self.workerCount = self.workerCount + 1 # increment the number of running workers
					(priority, target) = self.queue.get_nowait()
					self.inprogress.add(target)

				# Without the lock, run the function
				log.debug("Worker running target %s with priority %s", target, priority)
				failed = False
				errs = []
				keepgoing = False
				enqueue = []
				try:
					self.utilisation.incr()
					try: 
						(enqueue, errs, keepgoing) = self.fn(target)
					except Exception as e: 
						log.exception('Serious problem in thread pool worker: ') # log it but mustn't throw and miss the code below
						errs.append('Serious problem in thread pool worker: %r'%e)
						failed = True
				finally:
					self.utilisation.decr()

				# Take the lock again to update the errors, pending items in the queue and decrement the number of running workers
				with self.lock:
					log.debug("Updating errors and queue contents")
					self._errors.extend(errs)
					if not failed:
						for i in enqueue:
							self.queue.put_nowait(i)
					if not keepgoing:
						self.running = False
					self.workerCount = self.workerCount - 1
					self.completed = self.completed + 1
					self.inprogress.remove(target)
					
					self.condition.notifyAll()

		finally:
			if self.profile:
				profiler.disable()
				profiler.create_stats()
				with self.lock:
					self.threadProfiles.append(profiler)
					"""
					# in case we ever need per-thread profile data:
					dirpath = os.path.join(os.getcwd(), 'profile-xpybuild-%s' % os.getpid())
					mkdir(dirpath)
					file = os.path.join(dirpath, "%s-thread-%s" % (self.name, threading.current_thread().name))
					if os.path.exists(file): # probably won't ever happen
						index=0
						while os.path.exists(file+'.%s' % index):
							index = index + 1
						file+'.%s' % index
					profiler.dump_stats(file)
					"""

			with self.lock:
				self.condition.notifyAll()
	

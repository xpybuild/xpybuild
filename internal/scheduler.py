# xpyBuild - eXtensible Python-based Build System
#
# This class is responsible for working out what tasks need to run, and for 
# scheduling them
#
# Copyright (c) 2013 - 2017 Software AG, Darmstadt, Germany and/or its licensors
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
# $Id: scheduler.py 301527 2017-02-06 15:31:43Z matj $
#

import traceback, os, re, stat
from basetarget import BaseTarget
from buildcommon import *
from buildcontext import BuildContext
from buildexceptions import BuildException
from internal.buildtarget import BuildTarget
from internal.threadpool import ThreadPool, Utilisation
from internal.outputbuffering import outputBufferingManager
from utils.fileutils import deleteFile, exists, isfile, isdir, resetStatCache, getstat, toLongPathSafe
from utils.timeutils import formatTimePeriod
from threading import Lock

import time
import thread
import logging
import Queue
import random

log = logging.getLogger('scheduler')
		
class BuildScheduler(object):
	"""
		Master controller that takes a list of targets from the build files
		and a set requested on the command line along with the options and
		kicks them all off.
	"""
	
	def __init__(self, init, targets, options):
		"""
			Create a BuildScheduler.
			init - the BuildInitializationContext
			targets - the selected targets to build this run (list of target objects)
			options - the options for the build (map of string:variable)
		"""
		self.targetTimes = {} # map of {name : (path, seconds)}
		self.targets = None # map of targetPath:BuildTarget where targetPath is the canonical resolved path (from getFullPath)
		self.context = None
		self.pending = None # list of targetPaths
		self.options = None
		self.leaves = None
		self.lock = None
		self.built = 0
		self.completed = 0 # include built plus any deemed to be up to date

		resetStatCache() # at this point reread the stats of files, rather than using potentially stale cached ones

		self.targets = {}
		caseInsensitivePaths = set()
		
		self.progressFormat = str(len(str(len(init.targets()))))
		self.progressFormat = '*** %'+self.progressFormat+'d/%'+self.progressFormat+'d '
		
		for t in init.targets().values():
			try:
				# this is also a good place to resolve target names into paths
				t._resolveTargetPath(init)
				
				# do some sanity checking to catch common errors
				if t.path.lower() in caseInsensitivePaths:
					raise BuildException('Duplicate target path "%s"'%(t.path))
				caseInsensitivePaths.add(t.path.lower())
				
				assert isDirPath(t.path) == isDirPath(t.name) # must have agreement on whether it's a dir or file target between these different representations
				
				for o in init.getOutputDirs():
					if t.path.rstrip('\\/') == o.rstrip('\\/'):
						raise BuildException('Cannot use shared output directory for target: directory targets must always build to a dedicated directory')
						
				self.targets[t.path] = BuildTarget(t)
			except Exception, e:
				if not isinstance(e, IOError):
					log.exception('FAILED to prepare target %s: '%t) # include python stack trace in case it's an xpybuild bug
				# ensure all exceptions from here are annotated with the location and target name
				raise BuildException('FAILED to prepare target %s'%t, causedBy=True, location=t.location)
		
		self.context = BuildContext(init, set(self.targets.keys()))
		
		for dtarget in self.targets:
			if isDirPath(dtarget):
				for t in self.targets:
					if t.lower().startswith(dtarget.lower()) and t != dtarget: # we compare using the resolved paths
						raise BuildException('Multiple targets are not permitted to write output to the same directory: "%s" and "%s" (this would break the build as dependency tracking and parallelism rely on each target\'s output being isolated to a unique location)'%(
							self.targets[dtarget].name, self.targets[t].name), location=self.targets[t].location)
		
		self.context._resolveTargetGroups()

		self.pending = list([t.path for t in targets])
		self.pending.sort() # ensure a stable order that doesn't depend on hash maps
		
		self.options = options
		self.leaves = []
		self.lock = Lock()

		self.utilisation = Utilisation(options["workers"]) if options["logCPUUtilisation"] else None
	
	def _handle_error(self, target, prefix='Target FAILED'):
		""" Perform logging for the exception on the stack, and return an array of 
		string to be appended to the global build errors list. 
		
		target - should be a BaseTarget (not a BuildTarget)
		prefix - Prefix of exception, describing what we were doing at the time
		"""
		e = sys.exc_info()[1]
		
		logged = False
		
		if not isinstance(e, BuildException):
			if not isinstance(e, (EnvironmentError)):
				# most problems should be wrapped as BuildException already; let's make sure we always
				# get an ERROR-level message for things like syntax errors etc
				#log.exception('%s: unexpected (non-build) exception in %s'%(prefix, target))
				#logged = True
				pass # this duplicates the stack trace we get at ERROR level from toMultiLineString
				
			e = BuildException('%s due to %s'%(prefix, e.__class__.__name__), causedBy=True)
	
		if not logged and log.isEnabledFor(logging.DEBUG): # make sure the stack trace is at least available at debug
			log.debug('Handling error: %s', traceback.format_exc())
		
		# one-line summary (if in teamcity mode, we'd use teamcity syntax to log this)
		#log.error('%s: %s', prefix, e.toSingleLineString(target))
		# also useful to have the full stack trace, but only at INFO level
		#log.info('%s (details): %s\n', prefix, e.toMultiLineString(target, includeStack=True))

		# one-line summary (if in teamcity mode, we'd use teamcity syntax to log this)
		#log.error('%s: %s', prefix, e.toSingleLineString(target))
		
		# also useful to have the full stack trace, but only at INFO level
		log.error('%s: %s\n', prefix, e.toMultiLineString(target, includeStack=True), extra=e.getLoggerExtraArgDict(target))

		return [e.toSingleLineString(target)]
		
				
	def _run_target(self, target):
		"""
			Run a single target, calling clean or run appropriately and counting the time taken
			target - the target object to build
			number - how far through the build are we
			total - the total number of targets to (potentially) build
			Returns a list of error(s) encountered during the build
		"""
		
		errors = []
		
		log.info("%s: executing", target.name)
		duration = time.time()
		try:
			if self.options["clean"]:
				try:
					target.clean(self.context)
				except Exception as e:
					errors.extend(self._handle_error(target.target, prefix='Target clean FAILED'))
			else:
				# must always clean before running, in case there's some incorrect junk around 
				# in output dir or work dir from a previous execution; 
				# doing this means we don't require a full clean when a target incremental build 
				# fails
				try:
					log.debug('%s: Performing pre-execution clean', target.name)
					target.internal_clean(self.context) # removes the target and work dir, but doesn't call target-specific clean
				except Exception as e:
					errors.extend(self._handle_error(target.target, prefix='Target pre-execution clean FAILED'))
				
				# run the target
				try:
					if not errors:
						# if it's enabled, this is the point we want log statements 
						# to get buffered for writing to the output at the end of 
						# this target's execution
						outputBufferingManager.startBufferingForCurrentThread()
	
						log.debug('%s: executing run method for target', target.name)
						target.run(self.context)
				except Exception as e:
					errors.extend(self._handle_error(target.target))
					
					# if it failed we MUST delete the stamp file so it rebuilds next time, but 
					# probably useful to not delete the target as it might help tracking 
					# down the error; and definitely don't want to nuke the work dir which often 
					# contains invaluable log files - so don't actually call clean here
					try:
						deleteFile(target.stampfile)
					except Exception:
						# hopefully won't happen ever
						errors.extend(self._handle_error(target.target, prefix='ERROR deleting target stampfile after target failure'))
					
			duration = time.time() - duration
			
			if not self.options["clean"]:
				self.targetTimes[target.name] = (target.path, duration)
			log.critical("    %s: done in %.1f seconds", target.name, duration)
			return errors
		finally:
			outputBufferingManager.endBufferingForCurrentThread()
	
	def _expand_deps(self):
		"""
			Run over the list of targets to build, expanding it with all the dependencies and processing them
			for replacements and expansions. Also builds up the initial leaf set self.leaves and all the rdepends of each
			target (self.pending), along with the total number of dependencies each target has.
		"""
		self.index = 0 # identifies thread pool item n out of total=len(self.pending)
		self.total = len(self.pending) # can increase during this phase
		pending = Queue.Queue()
		for i in self.pending:
			pending.put_nowait((0, i))

		pool = ThreadPool('dependencychecking', self.options["workers"], pending, self._deps_target, self.utilisation, profile=self.options["profile"])

		pool.start()

		pool.wait()

		pool.stop()
		#assert (not pool.errors) or (self.total == self.index), (self.total, self.index) #disabled because assertion triggers during ctrl+c
		return pool.errors

	def _updatePriority(self, target):
		if target.deps:
			for d in target.deps:
				dt = self.targets.get(d, None)
				if dt: 
					with dt.lock:
						if dt.priority > target.priority:
							log.debug("Setting priority=%s on target %s", target.priority, dt.name)
							dt.setPriority(target.priority)
							self._updatePriority(dt)

	def _deps_target(self, tname):
		"""
			Function called by a worker to check the deps for a single target
			
			tname - this is the canonical PATH of the target, not the name
		"""
		errors = []
		pending = [] # list of new jobs to done as part of dependency resolution
		log.debug("Inspecting dependencies of target %s", tname)			
		target = self.targets.get(tname, None)

		# only log dependency status periodically since usually its very quick
		# and not worthwhile
		with self.lock:
			self.index += 1
			log.critical(self.progressFormat+"Resolving dependencies for %s", self.index, self.total, target)

		if not target:
			assert False # I'm not sure how we can get here, think it should actually be impossible
			if not exists(tname):
				errors.append("Unknown target %s" % tname)
			else:
				log.debug('Scheduler cannot find target in build file or on disk: %s', target) # is this a problem? maybe assert False here?
		elif self.options['ignore-deps'] and exists(target.path): 
			# in this mode, any target that already exists should be treated as 
			# a leaf with no deps which means it won't be built under any 
			# circumstances (even if a target it depends on is rebuilt), 
			# and allows us to avoid the time-consuming transitive resolution 
			# of dependencies. Has to be implemented this way, since if we were 
			# to allow ANY already-existing target to be re-built in the normal 
			# way, we would have to resolve dependencies for all targets in 
			# order to ensure we never rebuild a target at the same time as 
			# a target that depends on it. We're essentially deleting the entire 
			# dependency subtree for all nodes that exist already
			log.debug('Scheduler is treating existing target as a leaf and will not rebuild it: %s', target)
			self.leaves.append(target)
		elif not (self.options['ignore-deps'] and self.options['clean']): 
			try:
				deps = target.resolveDependencies(self.context)
				if deps: log.debug('%s has %d dependencies', target.target, len(deps))
				
				targetDeps = [] # just for logging
				
				leaf = True
				for dname in deps:
					#log.debug('Processing dependency: %s -> %s', tname, dname)
					dpath = toLongPathSafe(dname)
					dnameIsDirPath = isDirPath(dname)
					
					if dname in self.targets:
						leaf = False
						
						dtarget = self.targets[dname]
						if dtarget in target.rdeps(): raise Exception('Circular dependency between targets: %s and %s'%(dtarget.name, target.name))
						
						dtarget.rdep(target)
						self._updatePriority(target)
						target.increment()
						
						
						if not dnameIsDirPath:
							target.filedep(dname) # might have an already built target dependency which is still newer
						else:
							# special case directory target deps - must use stamp file not dir, to avoid re-walking 
							# the directory needlessly, and possibly making a wrong decision if the dir pathset is 
							# from a filtered pathset
							target.filedep(self.targets[dname].stampfile)						
					
						with self.lock:
							if not dname in self.pending:
								self.pending.append(dname)
								pending.append((0, dname))
						
						targetDeps.append(str(self.targets[dname]))
					else:
						dstat = getstat(dpath)
						if dstat and ( (dnameIsDirPath and stat.S_ISDIR(dstat.st_mode)) or (not dnameIsDirPath and stat.S_ISREG(dstat.st_mode)) ):
							target.filedep(dname)
						else:
							# in the specific case of a dependency error, build will definitely fail immediately so we should log line number 
							# at ERROR log level not just at info
							ex = BuildException("Cannot find dependency %s" % dname)
							log.error('FAILED during dependency resolution: %s', ex.toMultiLineString(target, includeStack=False), extra=ex.getLoggerExtraArgDict(target))
							assert not os.path.exists(dpath), dname
							errors.append(ex.toSingleLineString(target))
							
							break
						
				if leaf:
					log.info('Target dependencies of %s (priority %s) are: <no dependencies>', target, -target.priority)
					self.leaves.append(target)
				else:
					log.info('Target dependencies of %s (priority %s) are: %s', target, -target.priority, ', '.join(targetDeps)) # this is important for debugging missing dependencies etc
					
			except Exception as e:
				errors.extend(self._handle_error(target.target, prefix="Target FAILED during dependency resolution"))
		else:
			# For clean ignoring deps we want to be as light-weight as possible
			self.leaves.append(target)
		
		if pending:
			# if we're adding some new jobs
			with self.lock:
				self.total += len(pending)
			
		# NB: the keep-going option does NOT apply to dependency failures 
		return (pending, errors, 0 == len(errors))

	def _build(self):
		"""
			Runs the build, processing each leaf and adding new things to the leaf
			sets as their dependencies are built. On error either keeps going or
			returns immediately
		"""

		self.total = len(self.pending)
		self.index = 0 # identifies thread pool item n out of total, protected by lock

		leaves = self.leaves
		self.leaves = Queue.PriorityQueue()
		for l in leaves:
			if 'randomizePriorities' in self.options:
				self.leaves.put_nowait((random.random(), l))
			else:
				self.leaves.put_nowait((l.priority, l))

		pool = ThreadPool('building', self.options["workers"], self.leaves, self._process_target, self.utilisation, profile=self.options["profile"])

		pool.start()

		pool.wait()

		pool.stop()

		if self.options["logCPUUtilisation"]:
			self.utilisation.logSampleStats(log)

		return pool.errors, self.built, self.completed, self.total

	def _process_target(self, target):
		"""
			Function called by a worker to build a single target
		"""
		errors = []
		newleaves = []
		try:
			# count items as we go along
			with self.lock:
				index = self.index = self.index + 1
				total = self.total
			if self.options["clean"] or not target.uptodate(self.context, self.options['ignore-deps']):
				if self.options["clean"]:
					log.critical(self.progressFormat+"Cleaning %s", index, total, target)
				else:
					log.critical(self.progressFormat+"Building %s", index, total, target)
				if not self.options["dry-run"]:
					errors.extend(self._run_target(target)) # run the actual target rule
				# make sure we rebuild rdeps
				for rd in target.rdeps():
					if not rd.dirty():
						log.info("Up-to-date check: %s must be rebuilt due to change in dependency %s", rd.name, target)
				with self.lock:
					self.built = self.built + 1
					self.completed = self.completed + 1
			else:
				if self.options['ignore-deps']:
					log.critical(self.progressFormat+"Target is not checked for up-to-dateness due to ignore-deps option: %s", index, total, target)
				else:
					if total < 25:
						log.critical(self.progressFormat+"Target is already up-to-date: %s", index, total, target)
					else:
						log.info(self.progressFormat+"Target is already up-to-date: %s", index, total, target)
				with self.lock:
					self.completed = self.completed+1
			# look at our rdeps to see if we can build any of them now
			if not errors: 
				for rd in target.rdeps():
					if 0 == rd.decrement():
						log.debug("%s is now leaf", rd.name)
						newleaves.append((rd.priority, rd))
		except Exception as e:
			errors.extend(self._handle_error(target.target, prefix="Target FAILED"))
		return (newleaves, errors, 0 == len(errors) or self.options["keep-going"])
	
	def run(self):
		"""
			Run the build taking the set of requested targets, 
			expanding it for dependencies and running each in order
		"""
		builderrors = []
		built = 0
		total = 0
		completed = 0
		log.critical('Starting dependency resolution phase')
		depstime = time.time()
		deperrors = self._expand_deps()
		depstime = time.time()-depstime
		if self.options.get("depGraphFile", None):
			createDepGraph(self.options["depGraphFile"], self, self.context)
			return deperrors+builderrors, built, completed, total
			
		if not deperrors or self.options["keep-going"]:
			log.critical('Starting %s execution phase; dependency resolution took %s'%
				('clean' if self.options['clean'] else 'build', formatTimePeriod(depstime)))
			builderrors, built, completed, total = self._build()

		if not deperrors and not builderrors and self.index != self.total:
			bad = [self.targets[dname] for dname in self.pending if self.targets[dname].depcount != 0]
			log.info('Unexpected build error - some scheduled targets did not execute, possible dependency graph cycle; unexecuted targets are: %s'%
				', '.join([bt.name for bt in bad]))
			
			# try to detect first cycle
			def findCycle(nodes, edgefn):
				todo = set(nodes)
				while todo:
					node = todo.pop()
					stack = [node]
					while stack:
						top = stack[-1]
						for node in edgefn(top):
							if node in stack:
								return stack[stack.index(node):]
							if node in todo:
								stack.append(node)
								todo.remove(node)
								break
						else: # else belongs to for
							node = stack.pop()
				return None
			cycleTargets = findCycle(bad, lambda bt:bt.rdeps())
			
			if cycleTargets:
				log.error('Build FAILED due to %d-target dependency cycle: \n   %s\n', len(cycleTargets), '\n   '.join(reversed([bt.name for bt in cycleTargets])))
				raise BuildException('Build failed due to %d-target dependency cycle: %s'%(len(cycleTargets), ', '.join(reversed([bt.name for bt in cycleTargets]))))
			
			raise Exception('Unexpected build error - some scheduled targets did not execute, possible dependency graph cycle: %s'%bad)
		
		return deperrors+builderrors, built, completed, total

def createDepGraph(file, scheduler, context):
	""" Create a .dot file with the build dependency graph """
	def _getKey(target):
		return re.sub(r"[${}/()+\\<>\. -]", "_", str(target));

	def _getPrintable(target):
		return re.sub(r"<.*>", "", re.sub(r"[{}]", "", str(target)))

	with open(file, 'w') as df:
		df.write("digraph targets {\n")
		for t in scheduler.pending:
			df.write('%s[label="%s"];\n' % (_getKey(scheduler.targets[t]), _getPrintable(scheduler.targets[t])))
			for d in scheduler.targets[t].resolveDependencies(context):
				if d in scheduler.targets:
					df.write('%s -> %s;\n' % (_getKey(scheduler.targets[d]), _getKey(scheduler.targets[t])))
		df.write("}\n")


def logTargetTimes(file, scheduler, context):
	""" Log the time, cumulative and critical-path times of all the targets.

	Also create a .dot file with the build graph and edge cumulative times
	"""

	def _getKey(target):
		return re.sub(r"[${}/()+\\<>\. -]", "_", str(target));

	def _getPrintable(target):
		return re.sub(r"<.*>", "", re.sub(r"[{}]", "", str(target)))

	def _formatTime(time):
		return "%0.2f" % time
	
	def _sumpath(path):
		sum = 0.0
		for (target, time) in path:
			sum = sum + time
		return sum

	def _printablePath(path):
		str = "\n"
		sum = 0.0
		path = list(path)
		path.reverse()
		for (target, time) in path:
			sum = sum + time
			str = str + "\t\t%s (%0.2f, %0.2f)\n" % (target.target.name, time, sum)
		return str

	def _sumDepTimes(target, scheduler, context, dots, curpath, critpath):
		""" Takes a target, recurses over all its dependencies and sums the time take as well as looking for the critical path.
		This is not called the most efficient way (it's O(n^2), rather than O(n), since we don't cache the data on the nodes).
		It's not used unless we're requesting times though, so unless it gets too bad it's acceptable.
		"""
		(_, time) = scheduler.targetTimes[target.name]
		sum = time;
		curpath=list(curpath) # clone the path to check whether we're actually improving the critical path
		curpath.append((target, time)) # append this node to the possible critical path
		if _sumpath(curpath) > _sumpath(critpath): # if we are, then replace the current one
			del critpath[:]
			critpath.extend(curpath) 

		maxcrit = 0 # find the maximum critical path below us
		for d in target.resolveDependencies(context):
			if d in scheduler.targets:
				(edgecrit, edgesum) = _sumDepTimes(scheduler.targets[d], scheduler, context, dots, curpath, critpath) # get the critical/sum time for this dependency
				dots.add('%s -> %s[label="%s"];\n' % (_getKey(scheduler.targets[d]), _getKey(target), _formatTime(edgesum)))
				sum = sum + edgesum
				if edgecrit > maxcrit:
					maxcrit = edgecrit # update our maximum
		dots.add('%s[label="{{%s|{%s|%s}}}"];\n' % (_getKey(target), _getPrintable(target), _formatTime(time), _formatTime(sum)))
		return (time+maxcrit, sum) # return the critical path sum and all deps sum

	log.critical("Analysing build times...")
	critpath = []
	with open(file+'.dot', 'w') as df:
		df.write("digraph times {\n")
		df.write("node[shape=Mrecord];\n")
		dots = set() # dot nodes and edges added to this set, to avoid duplicates
		with open(file+'.csv', 'w') as f:
			f.write('Target,Time,Cumulative,Critical Path\n')
			for name in scheduler.targetTimes: # Iterate over each target
				(path, time) = scheduler.targetTimes[name]
				target = scheduler.targets[path]
				(crittime, cumtime) = _sumDepTimes(target, scheduler, context, dots, [], critpath) # recurse, summing the times on all the deps
				f.write(name)
				f.write(',')
				f.write(str(time))
				f.write(',')
				f.write(str(cumtime))
				f.write(',')
				f.write(str(crittime))
				f.write('\n')
		df.writelines(list(dots))
		df.write("}\n")
	log.critical('Time taken for each target written to %s.csv and %s.dot', file, file)
	log.critical('Critical Path is: %s', _printablePath(critpath))



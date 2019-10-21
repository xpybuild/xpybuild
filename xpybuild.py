#!/usr/bin/env python3
#
# xpyBuild - eXtensible Python-based Build System
#
# Copyright (c) 2013 - 2019 Software AG, Darmstadt, Germany and/or its licensors
# Copyright (c) 2013 - 2019 Ben Spiller and Matthew Johnson
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
#
# $Id: xpybuild.py 305815 2017-04-13 17:20:20Z bsp $
# Requires: Python 2.7
#
# Goals:
#   - correct build
#   - fast, parallelisable, scalable build
#   - simple build files, all complexities abstracted away in reusable helper 
#       classes
#   - fail-early on build configuration bugs (e.g. setting an unknown property)
#
# Key concepts:
#   - properties - immutable values specified by build files or overridden on 
#       command line. May be path, a string, True/False or list. 
#       Can be evaluated using "${propertyName}. All properties must be defined 
#       in a build file before they can be used. 
#   - target - something that generates an output file (or directory)
#       if the output file doesn't exist or is out of date with respect to 
#       other targets it depends on; has the ability to clean/delete any 
#       generated output. 
#       Targets are named based on their output file, but may also have 
#       tags to make referring to them easier. 
#   - tag - an alias for a target or set of targets, grouped together to make 
#       running them easier from the command line
#

import sys, os, getopt, time, traceback, logging, multiprocessing, threading, re
from functools import reduce

if float(sys.version[:3]) < 2.7: raise Exception('xpybuild.py requires at least Python 2.7 - unsupported python version %s'%sys.version[:3])

# a general-purpose mechanism for adding extra python modules when invoking 
# xpybuild, useful for third party plugins that may only be present on some 
# user's systems, and/or for importing user-defined plugins such as output 
# formatters
if os.getenv('XPYBUILD_PYTHONPATH'):
	sys.path.extend(os.getenv('XPYBUILD_PYTHONPATH').split(os.pathsep))
if os.getenv('XPYBUILD_IMPORTS'):
	import importlib
	for i in os.getenv('XPYBUILD_IMPORTS').split(','):
		importlib.import_module(i)

from buildcommon import *
from buildcommon import _XPYBUILD_VERSION
from buildcontext import *
from utils.fileutils import mkdir, deleteDir
from propertysupport import defineOption, parsePropertiesFile
from internal.stacktrace import listen_for_stack_signal
from buildexceptions import BuildException
from utils.consoleformatter import _registeredConsoleFormatters, publishArtifact
from utils.timeutils import formatTimePeriod

import utils.teamcity # to get handler registered
import utils.visualstudio # needed to create the entry in _handlers
import utils.make # needed to create the entry in _handlers
import utils.progress # needed to create the entry in _handlers

import utils.platformutils 
from internal.outputbuffering import OutputBufferingStreamWrapper, outputBufferingManager

log = logging.getLogger('xpybuild')

_TASK_BUILD = 'build'
_TASK_CLEAN = 'clean'
_TASK_REBUILD = 'rebuild'
_TASK_LIST_TARGETS = 'listTargets'
_TASK_LIST_FIND_TARGETS = 'findTargets'
_TASK_LIST_PROPERTIES = 'listProperties'
_TASK_LIST_OPTIONS = 'listOptions'
_TASK_LIST_TARGET_INFO = 'listTargetInfo'

def main(args):
	""" Command line argument parser. 
	"""
	
	try:
		usage = [
'',
'eXtensible Python-based Build System %s on Python %s.%s.%s'% (_XPYBUILD_VERSION, sys.version_info[0], sys.version_info[1], sys.version_info[2]),
'',
'xpybuild.py [operation]? [options]* [property=value]* [-x] [target|tag|regex]* ', 
'',
'A regex containing * can be used instead of a target, but only if it uniquely ', 
'identifies a single target. ',
'',
'Special pseudo-tags:',
'  all                        Include all targets (default if none are provided)',
'',
'Special properties:',
'  OUTPUT_DIR=output          The main directory output will be written to',
'  BUILD_MODE=release         Specifies release, debug (or user-defined) mode',
'  BUILD_NUMBER=n             Build number string, for reporting and use by build',
'',
'Operations: ',
'  (if none is specified, the default operation is a normal build)',
'      --clean                Clean specified targets incl all deps (default=all)',
'      --rebuild              Clean specified targets incl all deps then build',
'                             (add --ignore-deps to rebuild just specified ',
'                             targets)',
'',
' --ft --find-targets <str>   List targets containing the specified substring', 
' --ti --target-info <str>    Print details including build file location for ',
'                             targets containing the specified substring',
'      --targets              List available targets and tags (filtered by any ', 
'                             target or tag names specified on the command line)',
'      --properties           List properties that can be set and their ',
'                             defaults in this build file',
'      --options              List the target options available to build rules ',
'                             and their default values in this build file',
'',
'Options:',
'   -x --exclude <target>     Specifies a target or tag to exclude (unless ',
'                             needed as a dependency of an included target) ',
'',
'   -J --parallel             Build in parallel (this is the default). ',
'                             The number of workers is determined from the ',
'                             `build.workers` build file option or else the ',
'                             number of CPUs and the XPYBUILD_WORKERS_PER_CPU ',
'                             environment varable (default is currently 1.0), ',
'                             with an upper limit for this machine from the ',
'                             XPYBUILD_WORKERS_PER_CPU variable. ',
'   -j --workers <number>     Override the number of worker threads to use for ',
'                             building. Use -j1 for single-threaded. ',
'                             (ignores any environment variables)',
'',
'   -k --keep-going           Continue rather than aborting on errors',
'',
'   -n --dry-run              Don\'t actually build anything, just print',
'                             what would be done (finds missing dependencies)',
'',
' --id --ignore-deps          Skip all dependency/up-to-date checking: only ', 
'                             clean/build targets that do not exist at all ',
'                             (faster builds, but no guarantee of correctness)', 
'',
'   -f --buildfile <file>     Specify the root build file to import ',
'                             (default is ./root.xpybuild.py)',
'',
'   -l --log-level LEVEL      Set the log level to debug/info/critical',
'   -L --logfile <file>       Set the log file location',
'      --timefile <file>      Dump the time for each target in <file> at the',
'                             end of the run',
'      --depgraph <file>      Just resolve dependencies and dump them to <file>',
'      --cpu-stats            Log CPU utilisation stats',
'      --random-priority      Randomizes build order',
'      --verify               Performs additional verifications during the ',
'                             build to to help detect bugs in the build files. ',
'                             [verify is currently an experimental feature]',
'      --profile              Profiles all the worker threads',
'   -F --format               Message output format.',
'                             Options:',
] + [
'                                - '+ h for h in _registeredConsoleFormatters
] + [

]
		if reduce(max, list(map(len, usage))) > 80:
			raise Exception('Invalid usage string - all lines must be less than 80 characters')

		# set up defaults
		properties = {} 
		buildOptions = { "keep-going":False, "workers":0, "dry-run":False, 
			"ignore-deps":False, "logCPUUtilisation":False, "profile":False, "verify":False } 
		includedTargets = []
		excludedTargets = []
		task = _TASK_BUILD
		buildFile = os.path.abspath('root.xpybuild.py')
		logLevel = None
		logFile = None
		findTargetsPattern = None
		format = "default"

		opts,targets = getopt.gnu_getopt(args, "knJh?x:j:l:L:f:F:", 
			["help","exclude=","parallel","workers=","keep-going",
			"log-level=","logfile=","buildfile=", "dry-run",
			"targets", 'target-info=', 'ti=', "properties", "options", "clean", "rebuild", "ignore-deps", "id",
			"format=", "timefile=", "ft=", "find-targets=", "depgraph=", 'cpu-stats', 'random-priority', 'profile', 'verify'])
		
		for o, a in opts: # option arguments
			o = o.strip('-')
			if o in ["?", "h", "help"]:
				print('\n'.join(usage))
				return 0
			elif o in ["x", "exclude"]:
				excludedTargets.append(a)
			elif o in ["f", "buildfile"]:
				buildFile = os.path.abspath(a)
			elif o in ['targets']:
				task = _TASK_LIST_TARGETS
			elif o in ['find-targets', 'ft']:
				task = _TASK_LIST_FIND_TARGETS
				findTargetsPattern = a
			elif o in ['target-info', 'ti']:
				task = _TASK_LIST_TARGET_INFO
				findTargetsPattern = a
			elif o in ['properties']:
				task = _TASK_LIST_PROPERTIES
			elif o in ['options']:
				task = _TASK_LIST_OPTIONS
			elif o in ['J', 'parallel']:
				buildOptions['workers'] = 0
			elif o in ['j', 'workers']:
				buildOptions['workers'] = int(a)
			elif o in ['l', 'log-level']:
				logLevel = getattr(logging, a.upper(), None)
			elif o in ['cpu-stats']:
				buildOptions["logCPUUtilisation"] = True
			elif o in ['random-priority']:
				buildOptions["randomizePriorities"] = True
			elif o in ['L', 'logfile']:
				logFile = a
			elif o in ['F', 'format']:
				format = None
				if a =='xpybuild': a = 'default' # for compatibility
				for h in _registeredConsoleFormatters:
					if h.upper() == a.upper():
						format = h
				if not format:
					print('invalid format "%s"; valid formatters are: %s'%(a, ', '.join(_registeredConsoleFormatters.keys())))
					print('\n'.join(usage))
					return 1
			elif o in ['clean']:
				task = _TASK_CLEAN
				buildOptions['keep-going'] = True
			elif o in ['rebuild']:
				task = _TASK_REBUILD
			elif o in ['id', 'ignore-deps']:
				buildOptions['ignore-deps'] = True
			elif o in ['k', 'keep-going']:
				buildOptions['keep-going'] = True
			elif o in ['n', 'dry-run']:
				buildOptions['dry-run'] = True
			elif o in ['timefile']:
				buildOptions['timeFile'] = a
			elif o in ['verify']:
				buildOptions['verify'] = True
			elif o in ['profile']:
				buildOptions['profile'] = True
			elif o in ['depgraph']:
				buildOptions['depGraphFile'] = a
			else:
				assert False, "unhandled option: '%s'" % o

		for o in targets: # non-option arguments (i.e. no -- prefix)
			arg = o.strip()
			if arg:
				if '=' in arg:
					properties[arg.split('=')[0].upper()] = arg.split('=')[1]
				else:
					includedTargets.append(arg)
			
		# default is all
		if (not includedTargets) or includedTargets==['']:
			includedTargets = ['all']
		
	except getopt.error as msg:
		print(msg)
		print("For help use --help")
		return 2
	
	threading.currentThread().setName('main')
	logging.getLogger().setLevel(logLevel or logging.INFO)

	if buildOptions["workers"] < 0: buildOptions["workers"] = 0 # means there's no override
	
	outputBufferingDisabled = buildOptions['workers']==1 
	# nb: it's possible workers=0 (auto) and will later be set to 1 but doesn't really matter much

	# initialize logging to stdout - minimal output to avoid clutter, but indicate progress
	hdlr = _registeredConsoleFormatters.get(format, None)
	assert hdlr # shouldn't happen
	wrapper = OutputBufferingStreamWrapper(sys.stdout, bufferingDisabled=outputBufferingDisabled)
	# actually instantiate it
	hdlr = hdlr(
		wrapper, 
		buildOptions) 
	if hdlr.bufferingDisabled: wrapper.bufferingDisabled = True
		
	hdlr.setLevel(logLevel or logging.WARNING)
	logging.getLogger().addHandler(hdlr)
	log.info('Build options: %s'%{k:buildOptions[k] for k in buildOptions if k != 'workers'})
	
	stdout = sys.stdout
	
	# redirect to None, to prevent any target code from doing 'print' statements - should always use the logger
	sys.stdout = None

	listen_for_stack_signal() # make USR1 print a python stack trace

	allTargets = ('all' in includedTargets) and not excludedTargets

	try:
		def loadBuildFile():
			init = BuildInitializationContext(properties)
			isRealBuild = (task in [_TASK_BUILD, _TASK_CLEAN, _TASK_REBUILD])
			init._defineOption("process.timeout", 600)
			init._defineOption("build.keepGoing", buildOptions["keep-going"])
			
			# 0 means default behaviour
			init._defineOption("build.workers", 0)
			
			init.initializeFromBuildFile(buildFile, isRealBuild=isRealBuild)
			
			# now handle setting real value of workers, starting with value from build file
			workers = int(init._globalOptions.get("build.workers", 0))
			# default value if not specified in build file
			if workers <= 0: 
				workers = multiprocessing.cpu_count() 
			if os.getenv('XPYBUILD_WORKERS_PER_CPU'):
				workers = min(workers, int(round(multiprocessing.cpu_count()  * float(os.getenv('XPYBUILD_WORKERS_PER_CPU')))))
			
			# machine/user-specific env var can cap it
			if os.getenv('XPYBUILD_MAX_WORKERS'):
				workers = min(workers, int(os.getenv('XPYBUILD_MAX_WORKERS')))
			
			# finally an explicit command line --workers take precedence
			if buildOptions['workers']: workers = buildOptions['workers']
			
			if workers < 1: workers = 1
			
			# finally write the final number of workers where it's available to both scheduler and targets
			buildOptions['workers'] = workers
			init._globalOptions['build.workers'] = workers
			
			return init

		if buildOptions['profile']:
			import cProfile, pstats
			profiler = cProfile.Profile()
			profiler.enable()

		init = loadBuildFile()

		# nb: don't import any modules that might define options (including outputhandler) 
		# until build file is loaded
		# or we may not have a build context in place yet#
		from internal.scheduler import BuildScheduler, logTargetTimes


		if buildOptions['profile']:
			profilepath = 'xpybuild-profile-%s.txt'%'parsing'
			with open(profilepath, 'w') as f:
				p = pstats.Stats(profiler, stream=f)
				p.sort_stats('cumtime').print_stats(f)
				p.dump_stats(profilepath.replace('.txt', '')) # also in binary format
				log.critical('=== Wrote Python profiling output to: %s', profilepath)

		def lookupTarget(s):
			tfound = init.targets().get(s,None)
			if not tfound and '*' in s: 
				
				matchregex = s.rstrip('$')+'$'
				try:
					matchregex = re.compile(matchregex, re.IGNORECASE)
				except Exception as e:
					raise BuildException('Invalid target regular expression "%s": %s'%(matchregex, e))
				matches = [t for t in init.targets().values() if matchregex.match(t.name)]
				if len(matches) > 1:
					print('Found multiple targets matching pattern %s:'%(s), file=stdout)
					print(file=stdout)
					for m in matches:
						print(m.name, file=stdout)
					print(file=stdout)
					raise BuildException('Target regex must uniquely identify a single target: %s (use tags to specify multiple related targets)'%s)
				if matches: return matches[0]
				
			if not tfound: raise BuildException('Unknown target name, target regex or tag name: %s'%s)
			return tfound

		# expand tags to targets here, and do include/exclude calculations
		selectedTargets = set() # contains BaseTarget objects
		for t in includedTargets:
			tlist = init.tags().get(t,None)
			if tlist:
				selectedTargets.update(tlist)
			else:
				selectedTargets.add(lookupTarget(t))
		for t in excludedTargets:
			tlist = init.tags().get(t,None)
			if tlist:
				selectedTargets.difference_update(tlist)
			else:
				selectedTargets.discard(lookupTarget(t))

		# convert findTargetsPattern to list
		if findTargetsPattern:
			findTargetsPattern = findTargetsPattern.lower()
			# sort matches at start of path first, then anywhere in name, finally anywhere in type
			# make 'all' into a special case that maps to all *selected* targets 
			# (could be different to 'all' tag if extra args were specified, but this is unlikely and kindof useful)
			findTargetsList = [t for t in sorted(
				 init.targets().values() if allTargets else selectedTargets, key=lambda t:(
					'/'+findTargetsPattern.lower() not in t.name.lower(), 
					findTargetsPattern.lower() not in t.name.lower(), 
					findTargetsPattern.lower() not in t.type.lower(), 
					t.name
					)) if findTargetsPattern in t.name.lower() or findTargetsPattern in t.type.lower() or findTargetsPattern == 'all']

		if task == _TASK_LIST_PROPERTIES:
			p = init.getProperties()
			print("Properties: ", file=stdout)
			pad = max(list(map(len, p.keys())))
			if pad > 30: pad = 0
			for k in sorted(p.keys()):
				print(('%'+str(pad)+'s = %s') % (k, p[k]), file=stdout)
				
		elif task == _TASK_LIST_OPTIONS:
			options = init.mergeOptions(None)
			pad = max(list(map(len, options.keys())))
			if pad > 30: pad = 0
			for k in sorted(options.keys()):
				print(("%"+str(pad)+"s = %s") % (k, options[k]), file=stdout)

		elif task == _TASK_LIST_TARGETS:
			if len(init.targets())-len(selectedTargets) > 0:
				print("%d target(s) excluded (unless required as dependencies): "%(len(init.targets())-len(selectedTargets)), file=stdout)
				for t in sorted(['   %-15s %s'%('<'+t.type+'>', t.name) for t in init.targets().values() if t not in selectedTargets]):
					print(t, file=stdout)
				print(file=stdout)
				
			print("%d target(s) included: "%(len(selectedTargets)), file=stdout)
			for t in sorted(['   %-15s %s'%('<'+t.type+'>', t.name) for t in selectedTargets]):
				print(t, file=stdout)
			print(file=stdout)

			if allTargets:
				print("%d tags(s) are defined: "%(len(init.tags())), file=stdout)
				for t in sorted(['   %-15s (%d targets)'%(t, len(init.tags()[t])) for t in init.tags()]):
					print(t, file=stdout)

		elif task == _TASK_LIST_TARGET_INFO:
			if findTargetsList == '*': findTargetsList = init.targets().values()
			for t in sorted(findTargetsList, key=lambda t:(t.type+' '+t.name)):
				print('- %s priority: %s, tags: %s, location: \n   %s'%(t, t.getPriority(), t.getTags(), t.location), file=stdout)

		elif task == _TASK_LIST_FIND_TARGETS:
			# sort matches at start of path first, then anywhere in name, finally anywhere in type
			for t in findTargetsList:
				# this must be very easy to copy+paste, so don't put anything else on the line at all
				print('%s'%(t.name), file=stdout)
				
		elif task in [_TASK_BUILD, _TASK_CLEAN, _TASK_REBUILD]:
			
			if not logFile:
				if includedTargets == ['all'] and not excludedTargets:
					buildtag = None
				else:
					buildtag = 'custom'
				logFile = _maybeCustomizeLogFilename(init.getPropertyValue('LOG_FILE'), 
					buildtag,
					task==_TASK_CLEAN)
			logFile = os.path.abspath(logFile)

			logdir = os.path.dirname(logFile)
			if logdir and not os.path.exists(logdir): mkdir(logdir)
			log.critical('Writing build log to: %s', os.path.abspath(logFile))

			hdlr = logging.FileHandler(logFile, mode='w', encoding='UTF-8')
			hdlr.setFormatter(logging.Formatter('%(asctime)s %(relativeCreated)05d %(levelname)-8s [%(threadName)s %(thread)5d] %(name)-10s - %(message)s', None))
			hdlr.setLevel(logLevel or logging.INFO)
			logging.getLogger().addHandler(hdlr)
			
			log.info('Using xpybuild %s from %s on Python %s.%s.%s', _XPYBUILD_VERSION, os.path.normpath(os.path.dirname(__file__)), sys.version_info[0], sys.version_info[1], sys.version_info[2])
			log.info('Using build options: %s', buildOptions)

			try:
				# sometimes useful to have this info available
				import socket, getpass
				log.info('Build running on %s as user %s', socket.gethostname(), getpass.getuser())
			except Exception as e:
				log.info('Failed to get host/user: %s', e)

			log.info('Default encoding for subprocesses assumed to be: %s (stdout=%s, preferred=%s)', 
				getStdoutEncoding(), stdout.encoding, locale.getpreferredencoding())
			
			try:
				# if possible, set priority of builds to below normal by default, 
				# to avoid starving machines (e.g. on windows) of resources 
				# that should be used for interactive processes
				if os.getenv('XPYBUILD_DISABLE_PRIORITY_CHANGE','') != 'true':
					utils.platformutils.lowerCurrentProcessPriority()
					log.info('Successfully changed process priority to below normal')
			except Exception as e:
				log.warning('Failed to lower current process priority: %s'%e)
			
			if buildOptions['ignore-deps']:
				log.warning('The ignore-deps option is enabled: dependency graph will be ignored for all targets that already exist on disk, so correctness is not guaranteed')
			
			try:
				DATE_TIME_FORMAT = "%a %Y-%m-%d %H:%M:%S %Z"
				
				errorsList = []
				if task in [_TASK_CLEAN, _TASK_REBUILD]:
					startTime = time.time()
					log.critical('Starting "%s" clean "%s" at %s', init.getPropertyValue('BUILD_MODE'), init.getPropertyValue('BUILD_NUMBER'), 
						time.strftime(DATE_TIME_FORMAT, time.localtime( startTime )))
					
					cleanBuildOptions = buildOptions.copy()
					cleanBuildOptions['clean'] = True
					if allTargets: cleanBuildOptions['ignore-deps'] = True
					scheduler = BuildScheduler(init, selectedTargets, cleanBuildOptions)
					errorsList, targetsBuilt, targetsCompleted, totalTargets = scheduler.run()
		
					if allTargets and not cleanBuildOptions['dry-run']: # special-case this common case
						for dir in init.getOutputDirs():
							deleteDir(dir)
		
					log.critical('Completed "%s" clean "%s" at %s after %s\n', init.getPropertyValue('BUILD_MODE'), init.getPropertyValue('BUILD_NUMBER'), 
						time.strftime(DATE_TIME_FORMAT, time.localtime( startTime )), formatTimePeriod(time.time()-startTime))
						
					if errorsList: 
						log.critical('XPYBUILD FAILED: %d error(s): \n   %s', len(errorsList), '\n   '.join(sorted(errorsList)))
						return 3
				
				if task == _TASK_REBUILD:
					# we must reload the build file here, as it's the only way of flushing out 
					# cached data (especially in PathSets) that may have changed as a 
					# result of the clean
					init = loadBuildFile()
				
				if task in [_TASK_BUILD, _TASK_REBUILD] and not errorsList:

					for cb in init.getPreBuildCallbacks():
						try:
							cb(BuildContext(init))
						except BuildException as be:
							log.error("Pre-build check failed: %s", be)
							return 7

					buildtype = 'incremental' if any(os.path.exists(dir) for dir in init.getOutputDirs()) else 'full'
					if not buildOptions['dry-run']:
						for dir in init.getOutputDirs():
							log.info('Creating output directory: %s', dir)
							mkdir(dir)
					
					startTime = time.time()
					log.critical('Starting %s "%s" build "%s" at %s using %d workers', buildtype, 
						init.getPropertyValue('BUILD_MODE'), init.getPropertyValue('BUILD_NUMBER'), 
						time.strftime(DATE_TIME_FORMAT, time.localtime( startTime )), 
						buildOptions['workers']
						)
					
					buildOptions['clean'] = False
					scheduler = BuildScheduler(init, selectedTargets, buildOptions)
					errorsList, targetsBuilt, targetsCompleted, totalTargets = scheduler.run()
					log.critical('Completed %s "%s" build "%s" at %s after %s\n', buildtype, init.getPropertyValue('BUILD_MODE'), init.getPropertyValue('BUILD_NUMBER'), 
						time.strftime(DATE_TIME_FORMAT, time.localtime( startTime )), formatTimePeriod(time.time()-startTime))
					if 'timeFile' in buildOptions:
						logTargetTimes(buildOptions['timeFile'], scheduler, init)
	
				if errorsList: 
					# heuristically: it's useful to have them in order of failure when a small number, but if there are 
					# lots then it's too hard to read and better to sort, so similar ones are together
					if len(errorsList)>=10: errorsList.sort()
						
					log.critical('*** XPYBUILD FAILED: %d error(s) (aborted with %d targets outstanding): \n   %s', len(errorsList), totalTargets-targetsCompleted, '\n   '.join(errorsList))
					return 4
				else:
					# using *** here means we get a valid final progress message
					log.critical('*** XPYBUILD SUCCEEDED: %s built (%d up-to-date)', targetsBuilt if targetsBuilt else '<NO TARGETS>', (totalTargets-targetsBuilt))
					return 0
			finally:
				publishArtifact('XPyBuild logfile', logFile)
		else:
			raise Exception('Task type not implemented yet - '+task) # should not happen
		
	except BuildException as e:
		# hopefully we don't end up here very often
		log.error('*** XPYBUILD FAILED: %s', e.toMultiLineString(None))
		return 5

	except Exception as e:
		log.exception('*** XPYBUILD FAILED: ')
		return 6
	
def _maybeCustomizeLogFilename(logFile, tagName, isClean):
	# when using default log file it's actually a really good idea to customize the name if 
	# doing a clean or a special build (e.g. a tag that launches an IDE), 
	# otherwise calling into xpybuild multiple 
	# times would overwrite the main log or cause access denied. if this ever becomes 
	# controversial could control it with an option
	# this becomes unwieldy if we generate a new name for every target combination, 
	# so only do this for tags
	logSuffix = ''
	if tagName:
		logSuffix += '-%s'%(tagName.replace(' ','_').replace('\\','.').replace('/','_'))
	if isClean:
		logSuffix += '-clean'
	if logSuffix:
		extPos = logFile.rfind('.')
		if extPos <= 0:
			logFile += logSuffix
		else:
			logFile = logFile[:extPos]+logSuffix+logFile[extPos:]
	return logFile
	
if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))

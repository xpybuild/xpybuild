# xpyBuild - eXtensible Python-based Build System
#
# Defines the classes used to hold build context during the initialization and 
# build stages
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
# $Id: buildcontext.py 301527 2017-02-06 15:31:43Z matj $
#
import sys, os, getopt, time, traceback, types
from buildcommon import *
from utils.flatten import flatten
from utils.buildfilelocation import BuildFileLocation
from buildexceptions import BuildException
from utils.functors import Composable, Compose
from utils.consoleformatter import publishArtifact
import traceback

import logging
log = logging.getLogger('xpybuild')


__buildInitializationContext = None


def getBuildInitializationContext():
	""" Return the context build used during build-file parsing and initialization.

	This should be used by any target or build file that needs to call context methods 
	during build-file parsing, but not once the build has started.
	"""
	global __buildInitializationContext

	if not __buildInitializationContext: # just for pydoc testing
		print "<using test initialization context>",
		return None
	assert __buildInitializationContext != 'build phase', 'cannot use this method once the build has started, use context argument instead'
		
	return __buildInitializationContext

def _setBuildInitializationContext(context):
	global __buildInitializationContext
	__buildInitializationContext = context

class BaseContext(object):
	""" Common functionality needed during initialization and build phases. 
	"""
	
	def __init__(self, initialProperties=None):
		""" Initializes a BaseContext object. 
		
		@param initialProperties: a dictionary of initial property values; 
		used by doc tests. 
		"""
		
		self._globalOptions = {} # global options in build file (must be in _definedOptions)
		self._properties = dict(initialProperties or {})

	def publishArtifact(self, displayName, path):
		""" Publishes the specified local path as an artifact, 
		if supported by the configured output format. 
		
		For example this can be used to publish log and error output if a target 
		fails. 

		Equivalent to calling L{utils.consoleformatter.publishArtifact}
		"""
		# this is a convenience method
		publishArtifact(displayName, path)

	def getPropertyValue(self, name):
		""" Get the value of the specified property or raise a BuildException if it doesn't exist.

		@param name: the property name (without ${...}) to retrieve. Must be a string.
		
		@return: For Boolean properties this will be a python Boolean, for everything else it will be a string. 
		
		>>> BaseContext({'A':'b','BUILD_MODE':'release'}).getPropertyValue('BUILD_MODE')
		'release'
		>>> BaseContext({'A':False}).getPropertyValue('A')
		False
		>>> BaseContext({'A':True}).getPropertyValue('A')
		True
		>>> BaseContext({'A':'b'}).getPropertyValue('UNDEFINED_PROPERTY')
		Traceback (most recent call last):
		...
		BuildException: Property "UNDEFINED_PROPERTY" is not defined
		>>> BaseContext({'A':'b'}).getPropertyValue(None)
		Traceback (most recent call last):
		...
		BuildException: Property "None" is not defined
		>>> BaseContext({'A':'b'}).getPropertyValue('')
		Traceback (most recent call last):
		...
		BuildException: Property "" is not defined
		
		"""
			
		result = self._properties.get(name)
		if result == None:
			# before throwing an exception, see if it's one of the special 
			# always-defined proprties. During parse phase we don't auto-define 
			# these until they are needed in case build wants to override them
			
			# nb: each item here corresponds to a getPropertyValue() call in initializeFromBuildFile
			if name=='OUTPUT_DIR':
				outputDir = getBuildInitializationContext().defineProperty('OUTPUT_DIR', getBuildInitializationContext()._rootDir+'/'+'buildoutput')
				getBuildInitializationContext().registerOutputDir(outputDir)
			elif name=='BUILD_MODE':
				getBuildInitializationContext().defineProperty('BUILD_MODE', 'release')
			elif name=='BUILD_NUMBER':
				getBuildInitializationContext().defineProperty('BUILD_NUMBER', str(int(time.time()))) # this is a suitably unique number (perhaps too unique? don't want to force rebuilds...)
			elif name=='BUILD_WORK_DIR':
				getBuildInitializationContext().defineProperty('BUILD_WORK_DIR', 
					os.path.normpath(getBuildInitializationContext().getPropertyValue('OUTPUT_DIR')+'/BUILD_WORK'))
			elif name=='LOG_FILE':
				getBuildInitializationContext().defineProperty('LOG_FILE', os.path.abspath("build.log"))
			else:
				raise BuildException('Property "%s" is not defined'%name)
			result = self._properties.get(name)
			assert result!=None, name
			
		return result
	
	def expandPropertyValues(self, string, expandList=False):
		""" Expand all ${PROP_NAME} properties in the specified string. 

		Use a double dollar to escape if needed, e.g. "$${foo}" will end up as 
		"${foo}" unescaped. This assumes expandPropertyValues is not called 
		more than once on the same string (it is not idempotent). 
		
		Boolean values are expanded to "true" or "false"

		Returns the expanded string, or raises BuildException if expansion fails.

		@param string: The string with unexpanded properties in ${...} to expand.
		May alternatively be a Composable object which will be later 
		evaluated using its resolveToString method.

		@param expandList: return a list not a string and expand exactly one ${VAR[]} to multiple list items.
		
		>>> BaseContext({'A':'b'}).expandPropertyValues(None)
		>>> BaseContext({'A':'b'}).expandPropertyValues('')
		''
		>>> BaseContext({'A':'b','BUILD_MODE':'release'}).expandPropertyValues(' ${BUILD_MODE} x ${BUILD_MODE} ')
		' release x release '
		>>> BaseContext({'A':'b','BUILD_MODE':'release'}).expandPropertyValues(' ${BUILD_MODE} x ${BUILD_MODE} ', expandList=True)
		[' release x release ']
		>>> BaseContext({'DIR':'dir', 'NAMES[]':'a, b, c', 'SUFFIX':'.jar'}).expandPropertyValues('${DIR}/${NAMES[]}${SUFFIX}', expandList=True)
		['dir/a.jar', 'dir/b.jar', 'dir/c.jar']
		>>> BaseContext({'DIR':'dir', 'NAMES[]':'a, ${NAMES2[]}', 'NAMES2[]':'b, c', 'SUFFIX':'.jar'}).expandPropertyValues('${DIR}/${NAMES[]}${SUFFIX}', expandList=True)
		['dir/a.jar', 'dir/b.jar', 'dir/c.jar']
		>>> BaseContext({'NAMES[]':'a, b, c'}).expandPropertyValues('$${${NAMES[]}}', expandList=True)
		['${a}', '${b}', '${c}']
		>>> BaseContext({'A':'a','B':'b'}).expandPropertyValues(Compose('${A}', '${B}'))
		'ab'
		>>> BaseContext({'A':'a'}).expandPropertyValues('x${A}x$${A}x${A}x$$${A}x')
		'xax${A}xax$${A}x'
		>>> BaseContext({'A':'a','B':'b','C':'c'}).expandPropertyValues(Compose('${A}', '${B}')+'${C}')
		'abc'
		>>> BaseContext({'A':'b'}).expandPropertyValues('${UNDEFINED_PROPERTY}')
		Traceback (most recent call last):
		...
		BuildException: Property "UNDEFINED_PROPERTY" is not defined
		>>> BaseContext({'A':'b'}).expandPropertyValues('${A')
		Traceback (most recent call last):
		...
		BuildException: Incorrectly formatted property string "${A"
		>>> BaseContext({'A[]':'a, b'}).expandPropertyValues('${A[]}${A[]}', expandList=True)
		Traceback (most recent call last):
		...
		BuildException: Cannot expand as a list a string containing multiple list variables
		
		"""
		if not string: return string
		if hasattr(string, 'resolveToString'):
			string = string.resolveToString(self)
		assert isinstance(string, basestring), 'Error in expandPropertyValues: expecting string but argument was of type "%s"'%(string.__class__.__name__)
		
		if '$${' in string:
			assert '<escaped_xpybuild_placeholder>' not in string
			string = string.replace('$${', '<escaped_xpybuild_placeholder>')

		isListExpansion = False
		prefix=""
		listPropName=None
		while '${' in string:
			try:
				start = string.index('${')
				propName = string[ start+2 : string.index('}', start) ]
				if expandList and propName.endswith('[]'):
					if isListExpansion: raise BuildException("Cannot expand as a list a string containing multiple list variables")
					isListExpansion = True
					prefix=string[:start]
					listPropName=propName
					string=string[string.index('}', start)+1:]
					continue
			except BuildException:
				raise
			except Exception:
				raise BuildException('Incorrectly formatted property string "%s"'%string)
			v = self.getPropertyValue(propName)
			# every language except python doesn't use Initialcaps for their booleans so this is much more useful behaviour
			if isinstance(v, bool): v = 'true' if v else 'false' 
			string = string.replace('${%s}' % propName, v)

		if isListExpansion:
			rv = []
			for x in self.expandListPropertyValue(listPropName):
				x = self.expandPropertyValues(x, expandList=True)
				for y in x:
					rv.append((prefix+y+string).replace('<escaped_xpybuild_placeholder>', '${'))
			return rv
		else:
			string = string.replace('<escaped_xpybuild_placeholder>', '${')
			if expandList:
				return [string]
			else:
				return string

	def expandListPropertyValue(self, propertyName):
		""" Get the list represented by the specified property or raise a 
		BuildException if it doesn't exist.

		@param propertyName: the property name (without ${...}) to retrieve. Must be a string 
		and end with "[]".
		"""
		assert not propertyName.startswith('$'), propertyName
		assert propertyName.endswith('[]'), propertyName
		value = self.getPropertyValue(propertyName)
		return map(lambda s: s.strip(), value.split(','))
	
	def getProperties(self):
		"""
		Return a new copy of the properties dictionary (values may be of any type). Do not use this method unless 
		really necessary (e.g. for keyword substitution) - in almost all cases it is better to simply specify the 
		required properties explicitly to getPropertyValue or expandPropertyValues. 
		
		>>> BaseContext({'A':'b'}).getProperties()
		{'A': 'b'}
		"""
		return self._properties.copy()

	def _recursiveExpandProperties(self, obj, expandList=False):
		"""
		Recurses over obj, replacing any strings it finds.
		>>> BaseContext({'test':'foo'})._recursiveExpandProperties('${test}')
		'foo'
		>>> BaseContext({'test':'foo'})._recursiveExpandProperties(['${test}', '${test}'])
		['foo', 'foo']
		>>> BaseContext({'test':'foo'})._recursiveExpandProperties(('${test}', '${test}'))
		('foo', 'foo')
		>>> BaseContext({'test':'foo'})._recursiveExpandProperties({'${test}':'${test}'})
		{'foo': 'foo'}
		>>> BaseContext({'test':'foo'})._recursiveExpandProperties({'${test}1','${test}2'})
		set(['foo1', 'foo2'])
		>>> BaseContext({'test':'foo'})._recursiveExpandProperties({('${test}','${test}'):['${test}','${test}',{'${test}1','${test}2'}]})
		{('foo', 'foo'): ['foo', 'foo', set(['foo1', 'foo2'])]}
		"""
		if isinstance(obj, types.StringTypes):
			return self.expandPropertyValues(obj, expandList)
		elif isinstance(obj, tuple):
			newobj = []
			for i in obj:
				newobj.append(self._recursiveExpandProperties(i))
			return tuple(newobj)
		elif isinstance(obj, set):
			newobj = set()
			for i in obj:
				newobj.add(self._recursiveExpandProperties(i))
			return newobj
		elif isinstance(obj, list):
			newobj = []
			for i in obj:
				newobj.append(self._recursiveExpandProperties(i))
			return newobj
		elif isinstance(obj, dict):
			newobj = {}
			for k in obj:
				newobj[self._recursiveExpandProperties(k)] = self._recursiveExpandProperties(obj[k])
			return newobj
		elif isinstance(obj, Composable):
			return obj.resolveToString(self)
		else: return obj

	def defaultOptions(self):
		""" Returns a map of all the defined options and their default values. """
		return dict(_definedOptions)

	def mergeOptions(self, target=None, options=None): 
		""" [DEPRECATED] Merges together the default options, the globally overridden options and any set on the target.
		
		DEPRECATED: Use the target's self.options to get the resolved dictionary of options instead of this method. 

		This is usually called from within a target run() method. Any options provided on the target 
		will take priority, followed by anything overridden globally, finally anything left is taken
		from the option defaults.

		@param target: the target from which to take default options. If target is set then the map will
			also contain a 'tmpdir' option pointing at the target-specific work directory.

		@param options: options to override directly - this is retained for backwards compatibility only and should not be used. 

		@return: Returns a map of the merged options and their correct values.
		"""
		# maybe this should move into basetarget eventually
		if target: 
			fulloptions = { 'tmpdir' : target.workDir }
		else:
			fulloptions = {}
		# search defaults, then replace if in globals, then replace if in target.options
		for source in [_definedOptions, self._globalOptions, target and target._optionsTargetOverridesUnresolved or {}, options if options else {}]:
			if source:
				for key in source:
					try:
						if not key in _definedOptions.keys()+['tmpdir']: raise BuildException("Unknown option %s" % key)
						fulloptions[key] = self._recursiveExpandProperties(source[key])
					except BuildException, e:
						raise BuildException('Failed to resolve option "%s"'%key, location=target.location if target else None, causedBy=True)
		return fulloptions

	def getFullPath(self, path, defaultDir, expandList=False):
		""" Expands any properties in the specified path, then removes trailing path separators, normalizes it for this 
		platform and then makes it an absolute path if necessary, using the specified default directory. 
		
		@param path: a string representing a relative or absolute path. May be a string or a Composable
			
		@param defaultDir: the default parent directory to use if this is a 
		relative path; it is invalid to pass None for this parameter. 
		It is permitted to pass a BuildFileLocation for the defaultDir instead 
		of a string, in which case an exception will be thrown if it is an 
		empty location object and the path is relative; 
		this is primarily used for objects like PathSets that capture location 
		when they are instantiated.

		@param expandList: passed to expandPropertyValues, returns a list of 
		paths instead of a single path. 

		>>> BaseContext({'DEF':'output', 'EL':'element'}).getFullPath('path/${EL}', '${DEF}').replace('\\\\','/')
		'output/path/element'
		>>> BaseContext({'DEF':'output', 'EL':'element'}).getFullPath('/path/${EL}', '${DEF}').replace('\\\\','/')
		'/path/element'
		>>> BaseContext({'DEF':'output/', 'EL':'element'}).getFullPath('path/${EL}', '${DEF}').replace('\\\\','/')
		'output/path/element'
		>>> BaseContext({'DEF':'output/', 'EL':'element'}).getFullPath('path/../path/${EL}', '${DEF}').replace('\\\\','/')
		'output/path/element'
		"""
		assert defaultDir # non-empty string or BuildFileLocation
		
		def makeabs(p, defaultDir=defaultDir):
			if os.path.isabs(p): return p
			if isinstance(defaultDir, BuildFileLocation):
				defaultDir = defaultDir.buildDir
				# raise a non-build exception since this should not happen and 
				# we want a python stack trace
				if not defaultDir: raise Exception(
					'Cannot resolve relative path \'%s\' because the build file location is not available at this point; please either use an absolute path or ensure the associated object (e.g. PathSet) is instantiated while loading build files not while building targets'%p)
			else:
				defaultDir = self.expandPropertyValues(defaultDir)
			return os.path.join(defaultDir, p)
		
		if expandList:
			path = self.expandPropertyValues(path, expandList=expandList)
			rv = []
			for p in path:
				isdir = isDirPath(p)
				p = makeabs(p)
				p = normpath(p.rstrip('\\/'))
						
				if isdir and not p.endswith(os.path.sep): p = p+os.path.sep
				rv.append(p)
				
			return rv
		else:
			path = self.expandPropertyValues(path)
			isdir = isDirPath(path)
			path = makeabs(path)
			path = normpath(path.rstrip('\\/'))
					
			if isdir and not path.endswith(os.path.sep): path = path+os.path.sep
				
			return path
			
class BuildInitializationContext(BaseContext):
	"""
	Provides context used only during the initialization phase of the build, including the ability to change property 
	values that will later become immutable. Once initialization is complete, this object should be considered 
	immutable. 

	This is the class returned by L{getBuildInitializationContext}
	"""
	
	""" Manages the process of loading a build file, and contains the static 
	state of the build. 
	"""
	
	def __init__(self, propertyOverrides):
		""" Creates a new BuildInitializationContext object.

		Should only be called from within xpybuild, not from build files.
		   
		@param propertyOverrides: property override values specified by the user on the command line; all values must be 
		of type string. 
		"""
		
		BaseContext.__init__(self)

		self._propertyOverrides = dict(propertyOverrides)
		
		self._targetGroups = []
		self._targetsMap = {} # name:target object
		self._targetsList = [] # target objects
		self._tags = {} # tagName:list of targets
		self._outputDirs = set()
		self._initializationCompleted = False
		self._envPropertyOverrides = {}
		self._preBuildCallbacks = []
		
	
	def initializeFromBuildFile(self, buildFile, isRealBuild=True):
		""" Load the specified build file, which is the initialization phase during which properties are defined and 
		the build file target definitions will register themselves with this object. 

		Should only be called from within xpybuild, not from build files. To include another build file 
		instead use L{buildcommon.include}
			
		There should be very little (if any) accessing of the file system during this phase - all 
		per-target file system operations (e.g. dependency checking, globbing, etc) happens 
		later, to ensure the targets can be enumerated as fast as possible. 
		
		@param buildFile: The path to the build file to load.
		@param isRealBuild: True if this is going to be a real build, not just listing available targets etc
		"""
		self.__isRealBuild = isRealBuild
		if os.path.isdir(buildFile): buildFile = os.path.join(buildFile, 'root.xpybuild.py')
		sys.path.append(os.path.dirname(buildFile))
		startTime = time.time()
		log.debug("Loading build file ...")
		_setBuildInitializationContext(self)
		self._rootDir = os.path.abspath(os.path.dirname(buildFile))
		try:
			BuildFileLocation._currentBuildFile = [buildFile]
			execfile(buildFile, {})
			BuildFileLocation._currentBuildFile = []
		except BuildException, e:
			log.error('Failed to load build file: %s', e.toSingleLineString(None), extra=e.getLoggerExtraArgDict())
			log.debug('Failed to load build file: %s', traceback.format_exc())
			raise
		except SyntaxError, e:
			log.exception('Failed to load build file: ', extra={'xpybuild_filename':e.filename, 'xpybuild_line':e.lineno, 'xpybuild_col':e.offset})
			# wrap in buildexception to avoid printing same stack trace twice
			raise BuildException('Failed to load build file', causedBy=True)
		except Exception, e:
			log.exception('Failed to load build file: ')
			# wrap in buildexception to avoid printing same stack trace twice
			raise BuildException('Failed to load build file', causedBy=True)
			
		if time.time()-startTime > 1: # make sure it doesn't go undetected if this is taking a while
			log.critical('Loaded build files in %0.1f seconds', (time.time()-startTime))
		else:
			log.info('Loaded build files in %0.1f seconds', (time.time()-startTime))
		
		# Ensure special properties have been set (though typically this will 
		# be done near the start of the user build file)
		for p in ['OUTPUT_DIR', 'BUILD_MODE', 'BUILD_NUMBER', 'BUILD_WORK_DIR', 'LOG_FILE']:
			self.getPropertyValue(p) 

		# make sure this has been imported, since it's used for implementing many targets and defines some options of its own
		# which must happen before hte build phase begins
		import utils.outputhandler
		_setBuildInitializationContext('build phase')
		self._initializationCompleted = True
		
		# all the valid ones will have been popped already
		if self._propertyOverrides:
			raise BuildException('Cannot specify value for undefined build property/properties: %s'%(', '.join(self._propertyOverrides.keys())))
	
	def _initializationCheck(self):
		if self._initializationCompleted: raise Exception('Cannot invoke this method now that the initialization phase is over')
	
	def enableEnvironmentPropertyOverrides(self, prefix):
		if not prefix or not prefix.strip():
			raise BuildException('It is mandatory to specify a prefix for enableEnvironmentPropertyOverrides')
			
		# read from env now to save doing it repeatedly later
		for k in os.environ:
			if k.startswith(prefix):
				v = os.environ[k]
				k = k[len(prefix):]
				if k in self._envPropertyOverrides:
					# very unlikely, but useful to check
					raise BuildException('Property %s is being read in from the environment in two different ways'%(prefix+k))
				self._envPropertyOverrides[k] = v

	
	def defineProperty(self, name, default, coerceToValidValue=None, debug=False):
		""" Defines a user-settable property, specifying a default value and 
		an optional method to validate values specified by the user. 
		Return the value assigned to the property. 

		Build files should probably not use this directly, but instead call L{propertysupport.defineStringProperty}
		et al. Will raise an exception if called after the build files have been parsed.
		
		@param name: must be UPPER_CASE
		@param default: No substitution is performed on this value (see propertysupport.py if you need that).
		If set to None, the property must be set on the command line each time
		@param coerceToValidValue: None, or a function to validate and/or convert the input string to a value of the right 
		type
		@param debug: if True log at DEBUG else log at INFO
		"""
		self._initializationCheck()
		
		# enforce naming convention
		if name.upper() != name:
			raise BuildException('Invalid property name "%s" - all property names must be upper case'%name)

		if name in self._properties:
			raise BuildException('Cannot set the value of property "%s" more than once'%name)
		
		value = self._propertyOverrides.get(name)
		if value==None and name in self._envPropertyOverrides: 
			value = self._envPropertyOverrides.get(name)
			log.critical('Overriding property value from environment: %s=%s', name, value)
		if value==None: value = default 

		if value == None:
			raise BuildException('Property "%s" must be set on the command line' % name)

		# NB: from this point onwards value may NOT be a string (e.g. could be a boolean)
		if coerceToValidValue:
			# may change the value (e.g. to make the capitalization consistent or change the type) or throw an 
			# exception if it's invalid
			value = coerceToValidValue(value)
			
		self._properties[name] = value
		
		# remove if still present, so we can tell if user tries to set any undef'd properties
		self._propertyOverrides.pop(name, None) 
		
		if debug:
			log.debug('Setting property %s=%s', name, value)
		else:
			log.info('Setting property %s=%s', name, value)
		
		return value
	
	def registerOutputDir(self, outputDir):
		""" Registers that the specified directory should be created before the 
		build starts.
						 
		Build files should use L{propertysupport.defineOutputDirProperty} 
		instead of calling this function directly.
		Will raise an exception if called after the build files have been parsed.
		"""
		self._initializationCheck()
		
		self._outputDirs.add(outputDir)
	
	def registerTarget(self, target):
		""" Registers the target with the context.

		Called internally from L{basetarget.BaseTarget} and does not need to be called directly.
		Will raise an exception if called after the build files have been parsed.
		"""
		self._initializationCheck()
		
		# don't do anything much with it yet, wait for initialization phase to complete first
		if target.name in self._targetsMap:
			raise BuildException('Duplicate target name "%s" (%s)' % (target, self._targetsMap[target.name].location), location=target.location)
		self._targetsMap[target.name] = target
		self._targetsList.append(target)
		self.registerTags(target, target.getTags())

	def registerTags(self, target, taglist):
		""" Registers tags and their matching targets with the context.

		Called internally from L{basetarget.BaseTarget.tags} and does not need to be called directly.
		"""
		for t in taglist:
			targetsForTag = self._tags.get(t, [])
			if not targetsForTag: self._tags[t] = targetsForTag
			targetsForTag.append(target)

	def removeFromTags(self, target, taglist):
		""" Removes a target from a set of tags

		Called internally from L{basetarget.BaseTarget.disableInFullBuild}
		"""
		for tname in taglist:
			tlist = self._tags[tname] # if the tag does not exist, build file is broken and it should be an error
			
			# must do comparison based on name and not value of target, since we have no implemented equality
			self._tags[tname] = [x for x in tlist if x.name != target.name]

	def isRealBuild(self):
		""" Returns True if a real build is going to take place, or False if 
		the build files are just being parsed in order to list available 
		targets/properties. 
		
		This exists for the very special case of preventing expensive 
		initialization-phase operations if they're not really going to be 
		needed. 
		"""
		return self.__isRealBuild

	def registerPreBuildCheck(self, fn):
		""" Register a functor to be called before builds.
			 Functor should take a context and raise if the check fails """
		self._preBuildCallbacks.append(fn)

	def getPreBuildCallbacks(self):
		""" Return the list of pre-build callback functors """
		return self._preBuildCallbacks

	def getTargetsWithTag(self, tag):
		""" Returns the list of target objects with the specified tag name 
		(throws BuildException if not defined). 
		"""
		result = list(self._tags.get(tag, []))
		if not result:
			raise BuildException('Tag "%s" is not defined for any target in the build'%tag)
		return result



	def tags(self):
		""" Returns the map of tag names to lists of target objects
		"""
		return self._tags

	def targets(self):
		""" Return a map of targetName:target
		"""
		return self._targetsMap
		
	# methods used by the scheduler
	def getOutputDirs(self):
		""" Return the list of registered output dirs """
		return self._outputDirs

	def _defineOption(self, name, default):
		""" Register an available option and specify its default value.

		Called internally from L{propertysupport.defineOption} and does not 
		need to be called directly
		"""
		if name in _definedOptions and _definedOptions[name] != default:
			raise BuildException('Cannot define option "%s" more than once'%name)

		_definedOptions[name] = default
	def setGlobalOption(self, key, value):
		""" Set a global value for an option

		Called internally from L{propertysupport.setGlobalOption} and does not 
		need to be called directly
		"""
		if not key in _definedOptions:
			raise BuildException("Cannot specify value for option that has not been defined \"%s\"" % key)
		if key in self._globalOptions:
			log.warn("Resetting global option %s to %s at %s", key, value, BuildFileLocation().getLineString())
		else:
			log.info("Setting global option %s to %s at %s", key, value, BuildFileLocation().getLineString())
		self._globalOptions[key] = value

	def defineAtomicTargetGroup(self, targets):
		""" The given targets must all be built before anything which depends on any of those targets """
		targets = set(targets)
		self._targetGroups.append(targets)

	def _expandAtomicDeps(self, _deps):
		""" Takes a list of targets and adds in any extras due to atomic grouping """
		deps = set()
		for d in _deps:
			deps.add(d)
			if d in self._targetGroups:
				for t in self._targetGroups[d]:
					deps.add(t.path)
		return list(deps)


class BuildContext(BaseContext):
	"""
	Provides context used only during the build phase of the build (after initialization is complete), 
	i.e. the ability to expand variables (but not to change their value). 
	"""
	def __init__(self, initializationContext, targetPaths=None):
		""" Create a BuildContext from a L{BuildInitializationContext}. 
			
		Should not be used directly, will be passed into each target's run method.
		
		"""
		BaseContext.__init__(self, initializationContext.getProperties())
		self.init = initializationContext
		self._globalOptions = initializationContext._globalOptions
		self.__targetPaths = targetPaths
	
	def _resolveTargetGroups(self):
		""" Turns the list of groups of targets into a map of paths to target groups """
		targetGroups = {}
		for g in self.init._targetGroups:
			for t in g:
				assert not t in targetGroups
				targetGroups[t.path] = g
		self.init._targetGroups = targetGroups
	
	def getTargetsWithTag(self, tag):
		""" Returns the list of target objects with the specified tag name 
		(throws BuildException if not defined). 
		"""
		return self.init.getTargetsWithTag(tag)
		
	def _isValidTarget(self, target):
		""" Returns true if the specified target is known. Not intended for use 
		by build authors
		
		@param target: a target object, composeable, or string which may be the name or resolved path
		"""
		# nb: this exists because we deliberately don't want to expose targets 
		# in the build context, it shouldn't really be needed
		
		if hasattr(target, 'name'):
			return target.name in self.init.targets()
		target = str(target)
		return target in self.init.targets() or target in self.__targetPaths

	def _expandAtomicDeps(self, _deps):
		""" Takes a list of targets and adds in any extras due to atomic grouping """
		return self.init._expandAtomicDeps(_deps)

# hold option definitions outside of init context object, to support re-loading 
# build file (with a new init context) without losing definitions from 
# 'imported' modules (typically targets) which would not be reloaded due to 
# how python's module system works
_definedOptions = {} 

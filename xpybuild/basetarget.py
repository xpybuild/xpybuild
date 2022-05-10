# xpyBuild - eXtensible Python-based Build System
#
# Contains the base classes for creating various kinds of target. 
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
# $Id: basetarget.py 301527 2017-02-06 15:31:43Z matj $
#

"""
Contains `xpybuild.basetarget.BaseTarget` which contains 
methods such as `basetarget.BaseTarget.option`, `basetarget.BaseTarget.tags` for configuring the target instances 
in your build files, and is also the base class for defining new targets. 

"""

import os, inspect, shutil, re

from xpybuild.buildcommon import *
import xpybuild.buildcontext
from xpybuild.buildcontext import getBuildInitializationContext
import xpybuild.buildcontext
import xpybuild.utils.fileutils as fileutils
from xpybuild.utils.flatten import flatten, getStringList
from xpybuild.utils.buildfilelocation import BuildFileLocation
from xpybuild.utils.functors import Composable
from xpybuild.utils.buildexceptions import BuildException
from xpybuild.utils.fileutils import openForWrite, normLongPath, mkdir
import xpybuild.utils.stringutils

import logging

from xpybuild.propertysupport import defineOption

class BaseTarget(Composable):
	""" The base class for all targets. 
	
	.. rubric:: Configuring targets in your build files
	
	The following methods can be used to configure any target instance you add to a build file:
	
	.. autosummary ::
		option
		tags
		clearTags
		disableInFullBuild
		priority

	.. rubric:: Implementing a new target class
	
	If you are subclassing ``BaseTarget`` to create a new target class, you must implement `run`. 
	
	In rare occasions you may also wish to override `clean`. The following methods are available for use by target 
	subclasses, either at construction time (``__init__``) or at build time (during `run` or `clean`):

	.. autosummary ::
		registerImplicitInputOption
		registerImplicitInput
		getOption
		openFile
		targetNameToUniqueId
	
	This class provides several read-only attributes for use by subclasses.

	:ivar str name: The canonical name for the target (containing unsubstituted properties).
	
	:ivar str path: The resolved name with all properties variables expanded. This field is set only once the target is 
		running or checking up-to-dateness but not during initialization phase when targets are initially constructed.
	
	:ivar dict options: A ``dict`` of the resolved options for this target. Can only be used once target is running or 
		checking up-to-dateness but not during the initialization phase. See also `getOption()`.
	
	:ivar str workDir: A unique dedicated directory where this target can write temporary/working files.

	.. rubric:: Arguments for the BaseTarget __init__ constructor

	@param name: This target instance's unique name, which is the file or 
		directory path which is created as a result of running this target. 
		The target name may contain ``${...}`` properties (e.g. 
		``${OUTPUT_DIR}/myoutputfile``), and must use only forward slashes ``/``. 
		If the target builds a directory it must end with a forward slash. 
	
	@param dependencies: The dependencies, which may need to be 
		flattened/expanded by the build system; may be any combination of 
		strings, `xpybuild.pathsets`` and lists, and may also contain 
		unexpanded variables.
		
	.. rubric:: BaseTarget methods
	"""

	# to allow targets to be used in sets, override hash to ensure it's deterministic;
	# no need to override eq/ne, they use object identity which is already correct
	def __hash__(self): 
		"""
		Uses the target name to generate a hash. Targets are required to produce unique outputs.
		"""
		return hash(self.name)

	
	def __init__(self, name, dependencies):
		self.__getAttrImpl = {
			'path': lambda: self.__returnOrRaiseIfNone(self.__path, 'Target path has not yet been resolved by this phase of the build process: %s'%self),
			'name': lambda: self.__name,
			'options': lambda: self.__returnOrRaiseIfNone(self.__optionsResolved, "Cannot read the value of basetarget.targetOptions during the initialization phase of the build as the resolved option values are not yet available"),
			'workDir': lambda: self.__workDir,
			'type': lambda: self.__class__.__name__,
			'baseDir': lambda: self.location.buildDir,
		}
		
		self.__optionsTargetOverridesUnresolved = {} # for target-specific option overrides. for internal use (by buildcontext), do not use
		self.__optionsResolved = None # gets assigned during end of initialization phase

		if isinstance(name, str):
			if '//' in name:
				raise BuildException('Invalid target name: double slashes are not permitted: %s'%name)
			if '\\' in name:
				raise BuildException('Invalid target name: backslashes are not permitted: %s'%name)
		self.__name = BaseTarget._normalizeTargetName(str(name))
		self.__path_src = name
		self.__tags = ['full']
		self.__priority = 0.0 # default so we can go bigger or smaller
		self.log = logging.getLogger(self.__class__.__name__)
		
		# put the class first, since it results in better ordering (e.g. for errors)
		# use a space to delimit these to make it easier to copy to the clipboard by double-clicking
		self.__stringvalue = f'<{self.type}> {self.name}'
		
		init = getBuildInitializationContext()
		if not init: # doc-test mode
			self.location = BuildFileLocation(raiseOnError=False)
		else: 
			self.location = BuildFileLocation(raiseOnError=True)
			init.registerTarget(self) # this can throw

		# should ensure changes to the build file cause a rebuild? probs no need
		# PathSet will perform all necessary flattening etc
		self.__dependencies = PathSet(dependencies)
			
		self.__path = None # set by _resolveTargetPath
		self.__workDir = None
		
		self.__registeredImplicitInputs = []
		
		# aliases for pre-3.0
		self.addHashableImplicitInputOption = self.registerImplicitInputOption
		self.addHashableImplicitInput = self.registerImplicitInput

	@staticmethod
	def _normalizeTargetName(name): # non-public method to ensure comparisons between target names are done consistently
		if xpybuild.buildcontext._EXPERIMENTAL_NO_DOLLAR_PROPERTY_SYNTAX: 
			name = name.replace('$${', '<__xpybuild_dollar_placeholder>').replace('${', '{').replace('<__xpybuild_dollar_placeholder>', '$${')
		return name

	def __returnOrRaiseIfNone(self, value, exceptionMessage):
		if value is not None: return value
		raise Exception(exceptionMessage)

	def __setattr__(self, name, value):
		# this is a hack to retain backwards compat for a few classes that rely on explicitly assigning to self.options

		if name == 'options':
			# make this a WARN at some point
			self.log.debug('Target class "%s" assigns to self.options which is deprecated - instead call .option(...) to set target options'%self.__class__.__name__)
			if value:
				self.__optionsTargetOverridesUnresolved.update(value)
		else:
			object.__setattr__(self, name, value)

	def __getattr__(self, name):
		""" Getter for read-only attributes """
		# nb this is not called for fields that have been set explicitly using self.X = ...
		try:
			return self.__getAttrImpl[name]()
		except KeyError:
			raise AttributeError('Unknown attribute %s'%name)

	def __str__(self): # string display name which is used for log statements etc
		""" Returns a display name including the target name and the target type (class) """
		return self.__stringvalue

	def resolveToString(self, context):
		"""
		.. private:: There is usually no need for this to be called other than by the framework. 		
		Resolves this target's path and returns as a string. 
		
		It is acceptable to call this while the build files are still being 
		parsed (before the dependency checking phase), but an error will result 
		if resolution depends on anything that has not yet been defined. 
		"""
		
		# implementing this allows targets to be used in Composeable expressions
		
		# if there's no explicit parent, default to ${OUTPUT_DIR} to stop 
		# people accidentally writing to their source directories
		if self.__path is not None: return self.__path # cache it for consistency
		self.__path = context.getFullPath(self.__path_src, context.getPropertyValue("OUTPUT_DIR"))
		
		badchars = '<>:"|?*' # Windows bad characters; it's helpful to stop people using such characters on all OSes too since almost certainly not intended
		foundbadchars = [c for c in self.__path[2:] if c in badchars] # (nb: ignore first 2 chars of absolute path which will necessarily contain a colon on Windows)
		if foundbadchars: raise BuildException('Invalid character(s) "%s" found in target name %s'%(''.join(sorted(list(set(foundbadchars)))), self.__path))
		if self.__path.endswith(('.', ' ')): raise BuildException('Target name must not end in a "." or " "') # https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file
		
		self.log.debug('Resolved target name %s to canonical path %s', self.name, self.path)
		return self.__path

	def _resolveTargetPath(self, context):
		""".. private:: Internal method for resolving path from name, performing any 
		required expansion etc. 
		
		Do not override or call this method.
		
		@param context: The initialization context, with all properties and options fully defined. 
		"""
		self.resolveToString(context)

		# do this early (before deps resolution) so it can be used for clean
		self.__workDir = os.path.normpath(context.getPropertyValue("BUILD_WORK_DIR")+'/targets/'+self.__class__.__name__+'/'+targetNameToUniqueId(self.name))
		
		# take the opportunity to provide a merged set of options
		if len(self.__optionsTargetOverridesUnresolved)==0:
			self.__optionsResolved = context._globalOptions # since is immutable so we can avoid a copy
		else:
			self.__optionsResolved = context._mergeListOfOptionDicts([context._globalOptions, self.__optionsTargetOverridesUnresolved], target=self)

	def _resolveUnderlyingDependencies(self, context, rawdeps=False):
		""".. private:: Internal method for resolving dependencies needed by this target, 
		e.g. doing path expansion, globbing, etc. 
		
		Do not override this method. This method should be invoked only once, 
		by the scheduler. 
		"""
		# special option just for verify implementation, returning the real deps not the underlying deps
		if rawdeps: return self.__dependencies.resolve(context)
		
		# don't think there's any value in caching this result
		return self.__dependencies._resolveUnderlyingDependencies(context)

	def run(self, context: xpybuild.buildcontext.BuildContext):
		"""Called by xpybuild to request to target to run its build (all targets must implement this). 
		
		This method is only called when up-to-date checking shows that the target must be built. 
		It's possible that execution will show that the target did not really 
		need to execute, in which case False should be returned.  
		"""
		raise Exception('run() is not implemented yet for this target')

	def clean(self, context: xpybuild.buildcontext.BuildContext):
		"""Called by xpybuild when the target should be deleted (can be overridden if needed). 
		
		The default implementation will simply delete the target, and any target 
		workdir, but can be overridden to delete additional temporary files if 
		needed (shouldn't be).
		"""
		try:
			if self.workDir:
				fileutils.deleteDir(self.workDir)
		finally:
			if os.path.isdir(self.path):
				self.log.info('Target clean is deleting directory: %s', self.path)
				fileutils.deleteDir(self.path)
			else:
				fileutils.deleteFile(self.path)

	def registerImplicitInputOption(self, optionKey):
		"""Target classes can call this from their ``__init__()`` to add the resolved value of the specified option(s) as 
		'implicit inputs' of this target. 
		
		This list will be written to disk after the target builds successfully, and compared with its recorded value 
		when subsequently checking the up-to-date-ness of the target.
		This allows xpybuild to detect when the target should be rebuilt as a result of a change in options or property 
		values (e.g. build number, release/debug mode etc), even if no dependencies have changed. 
		
		Call this from the target's constructor, for each option that this target is affected by, 
		or with a callable that dynamically selects from the defined options, e.g. based on a prefix. 
		
		@param optionKey: the name of an option (as a string), 
			or a callable that accepts an optionKey and dynamically decides which options to include, 
			returning True if it should be included. For example::
		  
				self.registerImplicitInputOption(lambda optionKey: optionKey.startswith(('java.', 'javac.')))
		
		"""
		self.registerImplicitInput(lambda context: self.__getMatchingOptions(context, optionKey))

	def __getMatchingOptions(self, context, optionKey):
		if callable(optionKey):
			keys = [k for k in self.options if optionKey(k)]
		else:
			keys = [optionKey]
		result = []
		for k in sorted(keys):
			x = self.options[k]
			if x.__repr__.__qualname__ == 'function.__repr__': 
				value = x.__qualname__ # avoid 0x references for top-level functions (nb: doesn't affect lambas/nested functions)
			else:
				value = repr(x)
			#assert '0x' not in value
			result.append(f'option {k}={value}')
		return result

	def registerImplicitInput(self, item):
		"""Target classes can call this from their ``__init__()`` to add the specified string line(s) as 
		'implicit inputs' of this target. 
		
		This list will be written to disk after the target builds successfully, and compared with its recorded value 
		when subsequently checking the up-to-date-ness of the target.
		This allows xpybuild to detect when the target should be rebuilt as a result of a change in options or property 
		values (e.g. build number, release/debug mode etc), even if no dependencies have changed. 
		
		Call this from the target's constructor. 

		@param item: The item to be added to the implicit inputs. 
		
			This can be either:
		
				- a string, which may contain substitution variables, e.g. ``myparameter="${someprop}"``, 
				  and will converted to a string using `buildcontext.BuildContext.expandPropertyValues`, or
				- a callable to be invoked during up-to-dateness checking, that accepts a 
				  context parameter and returns a string or list of strings; 
				  any ``None`` items in the list are ignored. 
		"""
		assert isinstance(item, str) or callable(item)
		self.__registeredImplicitInputs.append(item)
	
	def getHashableImplicitInputs(self, context):
		"""(deprecated) Target classes can implement this to add the string line(s) as 'implicit inputs' of this target. 
		
		@deprecated: The `registerImplicitInput` or `registerImplicitInputOption` methods should be called 
		instead of overriding this method. 

		The default implementation returns nothing, unless 
		`registerImplicitInput` or `registerImplicitInputOption`
		have been called (in which case only the resolved paths of the file/directory dependencies will be used). 
		
		"""
		if self.__registeredImplicitInputs:
			result = []
			for x in self.__registeredImplicitInputs:
				if x is None: continue
				if callable(x) and not hasattr(x, 'resolveToString'): # if we aren't delegating to expandPropertyValues to resolve this
					x = x(context)
					if x is None: 
						continue
					elif isinstance(x, str):
						result.append(x)
					else: # assume it's a list or other iterable
						for y in x:
							if y is not None:
								result.append(y)
				else:
					result.append(context.expandPropertyValues(x))
			return result
		return []
	
	def getTags(self): 
		""" .. private:: Not exposed publically as there is no public use case for this. 
		
		@returns: The list of tags associated with this target. """
		return self.__tags

	def disableInFullBuild(self):
		"""Called by build file authors to configure this target to not build in ``all`` mode, so that it will only 
		be built if the target name or tag is specified on the command line (or if pulled in by a dependency).
		
		This is useful for targets that perform operations such as configuring developer IDEs which would not be 
		needed in the main build, or for expensive parts of the build that are often not needed such as generation 
		of installers. 
		
		See also `tag`. 
		"""
		self.__tags = list(set(self.__tags) - {'full'})
		init = getBuildInitializationContext()
		init.removeFromTags(self, ['full'])
		return self
	
	def clearTags(self):
		"""Called by build file authors to removes all tags other than ``all`` from this target.
		
		See `tag`. 
		"""
		init = getBuildInitializationContext()
		init.removeFromTags(self, self.__tags)
		self.__tags = ['full'] if 'full' in self.__tags else []
		init.registerTags(self, self.__tags)
		return self

	def getOption(self, key, errorIfNone=True, errorIfEmptyString=True):
		""" Target classes can call this during `run` or `clean` to get the resolved value of a specified option for 
		this target, with optional checking to give a friendly error message if the value is an empty string or None. 
		
		This is a high-level alternative to reading directly from `self.options`. 
		
		This method cannot be used while the build files are still being loaded, only during the execution of the targets. 
		"""
		if hasattr(key, 'optionName'): key = key.optionName # it's an Option instance

		if key not in self.options: raise Exception('Target tried to access an option key that does not exist: %s'%key)
		v = self.options[key]
		if (errorIfNone and v == None) or (errorIfEmptyString and v == ''):
			raise BuildException('This target requires a value to be specified for option "%s" (see basetarget.option or setGlobalOption)'%key)
		return v

	def option(self, key, value):
		"""Called by build file authors to configure this target instance with an override for an option value. 
		
		This allows target-specific overriding of options. If no override is provided, the value set in 
		`xpybuild.propertysupport.setGlobalOption` for the whole build is used, or if that was not set then the default 
		when the option was defined. 
		
		Use `self.options` or `getOption` to get resolved option values when implementing a target class. 
		
		@param str|xpybuild.propertysupport.Option key: The name of a previously-defined option. Usually this is a string 
		literal, but you cna also use the `xpybuild.propertysupport.Option` instance if you prefer. 
		
		@param value: The value. If the value is a string and contains any property values these will be expanded 
		before the option value is passed to the target. Use ``${{}`` to escape any literal ``{`` characters. 
		"""
		if hasattr(key, 'optionName'): key = key.optionName # it's an Option instance
		
		self.__optionsTargetOverridesUnresolved[key] = value
		return self
	
	def openFile(self, context: xpybuild.buildcontext.BuildContext, path: str, mode='r', **kwargs):
		"""Target classes can call this from their `run` implementation to open a specified file, using an encoding 
		specified by the ``common.fileEncodingDecider`` option (unless explicitly provided by ``encoding=``). 
		
		@param context: The context that was passed to run().
		@param path: The full absolute path to be opened. 
		@param mode: The file mode. 
		@keyword kwargs: Any additional arguments for the io.open() method can be specified here. 
		"""
		if 'b' not in mode and not kwargs.get('encoding'): kwargs['encoding'] = self.getOption('common.fileEncodingDecider')(context, path)
		return (openForWrite if 'w' in mode else io.open)(path, mode, **kwargs)
	
	def tags(self, *tags: str):
		"""Called by build file authors to append one or more tags to this target to make groups of related targets 
		easier to build (or just to provide a shorter alias for the target on the command line).

		@param tags: The tag, tags or list of tags to add to the target.
		
		>>> BaseTarget('a',[]).tags('abc').getTags()
		<using test initialization context> <using test initialization context> ['abc', 'full']
		>>> BaseTarget('a',[]).tags(['abc', 'def']).getTags()
		<using test initialization context> <using test initialization context> ['abc', 'def', 'full']
		>>> BaseTarget('a',[]).tags('abc', 'def').tags('ghi').getTags()
		<using test initialization context> <using test initialization context> <using test initialization context> ['ghi', 'abc', 'def', 'full']
		"""
		taglist = getStringList(list(tags))
		self.__tags = taglist + self.__tags
		assert sorted(list(set(self.__tags))) == sorted(list(self.__tags)) # check for duplicates
		init = getBuildInitializationContext()
		if init: init.registerTags(self, taglist) # init will be None during doctests
		return self

	def priority(self, priority: float):
		"""Called by build file authors to configure the priority of this target to encourage it (and its dependencies) 
		to be built earlier in the process. 
		
		The default priority is 0.0

		@param priority: a float representing the priority. Higher numbers will be built
			first where possible. Cannot be negative. 
		"""
		if priority < 0.0:
			raise BuildException('Target priority cannot be set to a lower number than 0.0')
		self.__priority = priority
		return self

	def updateStampFile(self):
		"""
		.. private:: Not useful enough to be in the public API. 
		
		Assumes self.path is a stamp file that just needs creating / timestamp updating and does so """
		path = normLongPath(self.path)
		mkdir(os.path.dirname(path))
		with openForWrite(path, 'wb') as f:
			pass

	
	def getPriority(self):
		""" .. private:: Not exposed publically as there is no public use case for this. 
		"""
		return self.__priority


	@staticmethod
	def targetNameToUniqueId(name: str) -> str:
		"""Convert a target name (containing unexpanded property values) into a convenient unique identifier. 
		
		The resulting identifier is not an absolute path, and (unless very long) does not contain any directory 
		elements. This id is suitable for temporary filenames and directories etc
		
		"""
		# remove chars that are not valid on unix/windows file systems (e.g. colon)
		x = re.sub(r'[^()+./\w-]+','_', name.replace('\\','/').replace('${','_').replace('{','_').replace('}','_').rstrip('/'))
		if len(x) < 256: x = x.replace('/','.') # avoid deeply nested directories in general
		return x

	class Options:
		""" Options for customizing the behaviour of all targets. To set an option on a specific target call 
		`xpybuild.basetarget.BaseTarget.option` or to se a global default use `xpybuild.propertysupport.setGlobalOption`. 
		"""
	
		failureRetries = defineOption("Target.failureRetries", 0)
		"""
		The "Target.failureRetries" option can be set on any target (or globally), and specifies how many times to retry 
		the target's build if it fails. The default is 0, which is recommended for normal developer builds. 

		There is an exponentially increasing backoff pause between each attempt - first 15s, then 30s, then 60s etc. 
		
		See `xpybuild.buildcommon.registerBuildLoadPostProcessor` which can be used to customize this option for targets based on 
		user-defined criteria such as target type. 
		"""

		failureRetriesInitialBackoffSecs = defineOption('Target.failureRetriesInitialBackoffSecs', 15) # undocumented as there should be no reason to change this

targetNameToUniqueId = BaseTarget.targetNameToUniqueId # alias for pre-3.0 projects
""".. private:: See static method instead.

.. deprecated:: Use `BaseTarget.targetNameToUniqueId` instead. 
"""


from xpybuild.pathsets import PathSet, BasePathSet

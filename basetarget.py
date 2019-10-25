0# xpyBuild - eXtensible Python-based Build System
#
# Contains the base classes for creating various kinds of target. 
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
# $Id: basetarget.py 301527 2017-02-06 15:31:43Z matj $
#

import os, inspect, shutil, re

from buildcommon import *
from buildcontext import getBuildInitializationContext
import utils.fileutils as fileutils
from utils.flatten import flatten, getStringList
from utils.buildfilelocation import BuildFileLocation
from utils.functors import Composable
from buildexceptions import BuildException
from utils.fileutils import openForWrite, normLongPath, mkdir
import targets.common # ensure common options are defined
import logging

class BaseTarget(Composable):
	""" The base class for all targets. All targets are uniquely identified by 
	a single name which is a file or a directory (ending with '/'). 
	
	Has public read-only attributes: 
	 - name: the unresolved canonical name for the target (containing unsubstituted properties etc).
	 - path: the resolved name with variables expanded etc. Can only be used once target is running or checking up-to-dateness but not during initialization phase.
	 - options: a dict of the resolved options for this target. Can only be used once target is running or checking up-to-dateness but not during initialization phase. See also L{getOption()}.
	 - workDir (a unique dedicated directory where this target can write 
	temporary/working files).
	
	The methods that may be overridden by subclasses are:
	 - L{run}
	 - L{clean}
	 - L{getHashableImplicitInputs}
	
	"""

	# to allow targets to be used in sets, override hash to ensure its deterministic
	# no need to override eq/ne, they use object identity which is already correct
	def __hash__(self): 
		"""
		Uses the target name to generate a hash. Targets are required to produce unique outputs.
		"""
		return hash(self.name)

	
	def __init__(self, name, dependencies):
		""" Normal constructor, should only be called from sub-classes since this is a stub.

		@param name: a unique name for this target (may contain unexpanded ${...}
		variables). Should correspond to the file or directory which is created
		as a result of running this target.
		@param dependencies: a list of dependencies, which may need to be 
		flattened/expanded by the build system; may be any combination of 
		strings, PathSets and lists and may also contain unexpanded variables.
		"""
		
		self._optionsTargetOverridesUnresolved = {} # for target-specific option overrides. for internal use (by buildcontext), do not use
		self.__optionsResolved = None # gets assigned during end of initialization phase

		if isinstance(name, str):
			if '//' in name:
				raise BuildException('Invalid target name: double slashes are not permitted: %s'%name)
			if '\\' in name:
				raise BuildException('Invalid target name: backslashes are not permitted: %s'%name)
		self.__name = str(name)
		self.__path_src = name
		self.__tags = ['all']
		self.__priority = 0.0 # default so we can go bigger or smaller
		self.log = logging.getLogger(self.__class__.__name__)
		
		init = getBuildInitializationContext()
		if not init: # doc-test mode
			self.location = BuildFileLocation(raiseOnError=False)
		else: 
			self.location = BuildFileLocation(raiseOnError=True)
			init.registerTarget(self)

		# should ensure changes to the build file cause a rebuild? probs no need
		# PathSet will perform all necessary flattening etc
		self.__dependencies = PathSet(dependencies)
			
		self.__path = None # set by _resolveTargetPath
		self.__workDir = None
		
		self.__hashableImplicitInputs = []

	def __setattr__(self, name, value):
		# this is a hack to retain backwards compat for a few classes that rely on explicitly assigning to self.options

		if name == 'options':
			# make this a WARN at some point
			self.log.debug('Target class "%s" assigns to self.options which is deprecated - instead call .option(...) to set target options'%self.__class__.__name__)
			if value:
				self._optionsTargetOverridesUnresolved.update(value)
		else:
			object.__setattr__(self, name, value)

	def __getattr__(self, name):
		""" Getter for read-only attributes """
		# nb this is not called for fields that have been set explicitly using self.X = ...
		
		if name == 'path': 
			if not self.__path: raise Exception('Target path has not yet been resolved by this phase of the build process: %s'%self)
			return self.__path
		if name == 'name': return self.__name
			
		if name == 'options': 
			# don't return self.options here, since a) that has the unresolved/unmerged options and b) setting it is 
			# dodgy and something that must work for compat reasons but which we want to discourage
			
			if self.__optionsResolved == None:
				# probably no-one is using this, but in case they are give a clear message
				# instead, should be setting the .option(...) method, and getting
				raise Exception("Cannot read the value of basetarget.targetOptions during the initialization phase of the build as the resolved option values are not yet available")
			return self.__optionsResolved
		
		if name == 'workDir': return self.__workDir
		if name == 'type': return self.__class__.__name__
		if name == 'baseDir': return self.location.buildDir
		raise AttributeError('Unknown attribute %s'%name)

	def __str__(self): # string display name which is used for log statements etc
		""" Returns a display name including the target name and the target type (class) """
		# put the class first, since it results in better ordering (e.g. for errors)
		# use a space to delimit these to make it easier to copy to the clipboard by double-clicking
		return '<%s> %s' % (self.type, self.name)

	def resolveToString(self, context):
		""" Resolves this target's path and returns as a string. 
		
		It is acceptable to call this while the build files are still being 
		parsed (before the dependency checking phase), but an error will result 
		if resolution depends on anything that has not yet been defined. 
		"""
		
		# implementing this allows targets to be used in Composeable expressions
		
		# if there's no explicit parent, default to ${OUTPUT_DIR} to stop 
		# people accidentally writing to their source directories
		if self.__path: return self.__path # cache it for consistency
		self.__path = context.getFullPath(self.__path_src, "${OUTPUT_DIR}")
		self.log.debug('Resolved target name %s to canonical path %s', self.name, self.path)
		return self.__path

	def _resolveTargetPath(self, context):
		""" Internal method for resolving path from name, performing any 
		required expansion etc. 
		
		Do not override this method.
		
		@param context: The initialization context, with all properties and options fully defined. 
		"""
		self.resolveToString(context)

		# do this early (before deps resolution) so it can be used for clean
		self.__workDir = os.path.normpath(context.getPropertyValue("BUILD_WORK_DIR")+'/targets/'+self.__class__.__name__+'/'+targetNameToUniqueId(self.name))
		
		# take the opportunity to provide a merged set of options
		self.__optionsResolved = context.mergeOptions(target=self)

	def _resolveUnderlyingDependencies(self, context, rawdeps=False):
		""" Internal method for resolving dependencies needed by this target, 
		e.g. doing path expansion, globbing, etc. 
		
		Do not override this method. This method should be invoked only once, 
		by the scheduler. 
		"""
		# special option just for verify implementation, returning the real deps not the underlying deps
		if rawdeps: return self.__dependencies.resolve(context)
		
		# don't think there's any value in caching this result
		return self.__dependencies._resolveUnderlyingDependencies(context)

	def run(self, context):
		""" Build this target. 
		
		Called after a failed up-to-date check to build this target. 
		It's possible that execution will show that the target did not really 
		need to execute, in which case False should be returned (so that dependent tasks do not 
		necessarily get rebuilt).  
		"""
		raise Exception('run() is not implemented yet for this target')

	def clean(self, context):
		""" Clean this target. 
		
		Default implementation will simply delete the target, and any target 
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

	def addHashableImplicitInputOption(self, optionKey):
		""" Adds a target-specific string giving information about an 
		implicit input of this target, to the list that will be returned
		getHashableImplicitInputs to help detect when the target should be rebuilt. 
		
		Call this for each option that this target is affected by. 
		
		See L{getHashableImplicitInputs} for more information.
		
		@param optionKey: the name of an option. 
		
		"""
		self.addHashableImplicitInput(lambda context: 'option %s=%s'%(optionKey, repr(self.options[optionKey])))
		
	def addHashableImplicitInput(self, item):
		""" Adds a target-specific string giving information about an 
		implicit input of this target to the list that will be returned by
		getHashableImplicitInputs to help detect when the target should be rebuilt. 
		
		This can include options, property values (e.g. changes in build number,
		release/debug mode) and glob results (e.g. addition or removal of a
		file should trigger a rebuild). 
		
		See L{getHashableImplicitInputs} for more information.
		
		@param item: a string (which may contain substitution variables), 
		or a function that accepts a context parameter and returns a string. 
		The item will converted to a string using L{buildcontext.BuildContext.expandPropertyValues}. 
		For example, 'myparameter="foobar"'. 
		
		"""
		assert isinstance(item, str) or callable(item)
		self.__hashableImplicitInputs.append(item)
	
	def getHashableImplicitInputs(self, context):
		""" Return a target-specific token (a list of strings) representing the 
		implicit inputs of this target that cannot be detected using normal 
		timestamp up-to-date checking.
												
		This can include options, property values (e.g. changes in build number,
		release/debug mode) and glob results (e.g. addition or removal of a
		file should trigger a rebuild). 
		
		This list will be written to disk (possibly hashed) after the target 
		builds successfully, and compared with its recorded value when 
		subsequently checking the up-to-date-ness of the target.
		
		The default implementation returns nothing, unless 
		L{addHashableImplicitInput} or L{addHashableImplicitInputOption} 
		have been called, so only the globbed and 
		resolved paths of any pathsets in the dependency list will be used. 
		
		Some targets should override this to append additional information, 
		such as relevant property or option values. Alternatively, for simple 
		cases call L{addHashableImplicitInput} or L{addHashableImplicitInputOption}. 
		"""
		if self.__hashableImplicitInputs:
			return list([context.expandPropertyValues(x) for x in self.__hashableImplicitInputs])
		return []
	
	def getTags(self): 
		""" Return the list of tags associated with this target """
		return self.__tags

	def disableInFullBuild(self):
		""" Stops this target from building in 'all' mode, therefore it must be called 
		explicitly or via a tag.
		"""
		self.__tags = list(set(self.__tags) - {'all'})
		init = getBuildInitializationContext()
		init.removeFromTags(self, ['all'])
		return self
	
	def clearTags(self):
		""" Removes any tags other than "all" from this target """
		init = getBuildInitializationContext()
		init.removeFromTags(self, self.__tags)
		self.__tags = ['all'] if 'all' in self.__tags else []
		init.registerTags(self, self.__tags)
		return self

	def getOption(self, key, errorIfNone=True, errorIfEmptyString=True):
		"""
		Gets the resolved value of a specified option for this target, with optional 
		checking to give a friendly error message if the value is an empty string or None. 
		"""
		if key not in self.options: raise Exception('Target tried to access an option key that does not exist: %s'%key)
		v = self.options[key]
		if (errorIfNone and v == None) or (errorIfEmptyString and v == ''):
			raise BuildException('This target requires a value to be specified for option "%s" (see basetarget.option or setGlobalOption)'%key)
		return v

	def option(self, key, value):
		"""
		Set an option on this target, overriding any default value provided by setGlobalOption. 
		If the value contains any property values these will be expanded before the option value is 
		passed to the target. 
		
		Use self.options or L{getOption} to get resolved option values. 
		"""
		self._optionsTargetOverridesUnresolved[key] = value
		return self
	
	def openFile(self, context, path, mode='r', **kwargs):
		"""
		Opens the specified file, using an encoding specified by the target option's 
		`common.fileEncodingDecider` (unless explicitly provided by encoding=). 
		
		@param context: The context that was passed to run().
		@param path: The full absolute path to be opened. 
		@param mode: The file mode. 
		@keyword kwargs: Any additional arguments for the io.open() method can be specified here. 
		"""
		if 'b' not in mode and not kwargs.get('encoding'): kwargs['encoding'] = self.getOption('common.fileEncodingDecider')(context, path)
		return (openForWrite if 'w' in mode else io.open)(path, mode, **kwargs)
	
	def tags(self, *tags):
		"""
		Append one or more 'tag' strings that will be associated with this target.

		These tags can be supplied on the command line to build associated groups of targets, 
		or just provide a shorter, well-known, name.

		@param tags: the tag, tags or list of tags to add to the target.
		
		>>> BaseTarget('a',[]).tags('abc').getTags()
		<using test initialization context> <using test initialization context> ['abc', 'all']
		>>> BaseTarget('a',[]).tags(['abc', 'def']).getTags()
		<using test initialization context> <using test initialization context> ['abc', 'def', 'all']
		>>> BaseTarget('a',[]).tags('abc', 'def').tags('ghi').getTags()
		<using test initialization context> <using test initialization context> <using test initialization context> ['ghi', 'abc', 'def', 'all']
		"""
		taglist = getStringList(list(tags))
		self.__tags = taglist + self.__tags
		assert sorted(list(set(self.__tags))) == sorted(list(self.__tags)) # check for duplicates
		init = getBuildInitializationContext()
		if init: init.registerTags(self, taglist) # init will be None during doctests
		return self

	def priority(self, priority):
		"""
		Set the priority of this target it encourage it (and its deps) to be 
		built earlier in the process. The default priority is 0.0

		@param priority: a float representing the priority. Higher numbers will be built
		first where possible. Cannot be negative. 
		"""
		if priority < 0.0:
			raise BuildException('Target priority cannot be set to a lower number than 0.0')
		self.__priority = priority
		return self

	def updateStampFile(self):
		""" Assumes self.path is a stamp file that just needs creating / timestamp updating and does so """
		path = normLongPath(self.path)
		mkdir(os.path.dirname(path))
		with openForWrite(path, 'wb') as f:
			pass

	
	def getPriority(self):
		""" Return the current priority of this target """
		return self.__priority

def targetNameToUniqueId(name):
	""" Munge a target name (unexpanded path) into an identifier that is 
	not an absolute path, and (unless very long) does not contain any directory 
	elements. This id is suitable for temporary filenames and directories etc
	
	"""
	# remove chars that are not valid on unix/windows file systems (e.g. colon)
	x = re.sub(r'[^()+./\w-]','_', name.replace('\\','/').replace('${','_').replace('}','_').rstrip('/'))
	if len(x) < 256: x = x.replace('/','.') # avoid deeply nested directories in general
	return x

from pathsets import PathSet, BasePathSet

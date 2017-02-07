# xpyBuild - eXtensible Python-based Build System
#
# Contains the base classes for creating various kinds of target. 
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
# $Id: basetarget.py 301527 2017-02-06 15:31:43Z matj $
#

import os, inspect, shutil, re

from buildcommon import *
from buildcontext import getBuildInitializationContext
import utils.fileutils as fileutils
from utils.flatten import flatten, getStringList
from utils.buildfilelocation import BuildFileLocation
from internal.functors import Composable
from buildexceptions import BuildException
import logging

class BaseTarget(Composable):
	""" The base class for all targets. All targets are uniquely identified by 
	a single name which is a file or a directory (ending with '/'). 
	
	Has public read-only attributes: 
		- name
		- path (resolved name with variables expanded etc)
		- workDir (a unique dedicated directory where this target can write 
			temporary/working files)
	
	The methods that may be overridden by subclasses are:
	- run
	- clean
	- getHashableImplicitInputs
	
	"""

	location = None
	__options = {}
	
	# to allow targets to be used in sets, override hash to ensure its deterministic
	# no need to override eq/ne, they use object identity which is already correct
	def __hash__(self): 
		"""
		Uses the target name to generate a hash. Targets are required to produce unique outputs.
		"""
		return hash(self.name)

	
	def __init__(self, name, dependencies):
		""" Normal constructor, should only be called from sub-classes since this is a stub.

		name -- a unique name for this target (may contain unexpanded ${...}
			variables). Should correspond to the file or directory which is created
			as a result of running this target.
		depenencies -- a list of dependencies, which may need to be 
			flattened/expanded by the build system; may be any combination of 
			strings, PathSets and lists and may also contain unexpanded variables.
		"""
		if isinstance(name, basestring):
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

	def __getattr__(self, name):
		""" Getter for read-only attributes """
		if name == 'path': 
			if not self.__path: raise Exception('Target path has not yet been resolved by this phase of the build process: %s'%self)
			return self.__path
		if name == 'name': return self.__name
		if name == 'options': return self.__options
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
		"""
		self.resolveToString(context)

		# do this early (before deps resolution) so it can be used for clean
		self.__workDir = os.path.normpath(context.getPropertyValue("BUILD_WORK_DIR")+'/targets/'+targetNameToUniqueId(self.name))

	def _resolveUnderlyingDependencies(self, context):
		""" Internal method for resolving dependencies needed by this target, 
		e.g. doing path expansion, globbing, etc. 
		
		Do not override this method. This method should be invoked only once, 
		by the scheduler. 
		"""
		# don't think there's any value in caching this result
		if not self.__dependencies: return []
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
	
	def getHashableImplicitInputs(self, context):
		""" Return a target-specific token (a list of strings) representing the 
		implicit inputs of this target that cannot be detected using normal 
		timestamp up-to-date checking.
												
		This can include property values (e.g. changes in build number,
		release/debug mode) and glob results (e.g. addition or removal of a
		file should trigger a rebuild). 
		
		This list will be written to disk (possibly hashed) after the target 
		builds successfully, and compared with its recorded value when 
		subsequently checking the up-to-date-ness of the target.
		
		The default implementation returns nothing, so only the globbed and 
		resolved paths of any pathsets in the dependency list will be used. 
		
		Some targets should override this to append additional information, 
		such as relevant property values. 
		"""
		
		return []
	
	def getTags(self): 
		""" Return the list of tags associated with this target """
		return self.__tags

	def disableInFullBuild(self):
		""" Stops this target from building in 'all' mode, therefore it must be called 
		explicitly or via a tag.
		"""
		self.__tags = list(set(self.__tags) - set(['all']))
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

	def option(self, key, value):
		"""
		Set an option on this target,
		"""
		self.__options[key] = value
		return self
	
	def tags(self, *tags):
		"""
		Append one or more 'tag' strings that will be associated with this target.

		These tags can be supplied on the command line to build associated groups of targets, 
		or just provide a shorter, well-known, name.

		tags -- the tag, tags or list of tags to add to the target.
		
		>>> BaseTarget('a',[]).tags('abc').getTags()
		<using test initialization context> <using test initialization context>
		['abc', 'all']
		>>> BaseTarget('a',[]).tags(['abc', 'def']).getTags()
		<using test initialization context> <using test initialization context>
		['abc', 'def', 'all']
		>>> BaseTarget('a',[]).tags('abc', 'def').tags('ghi').getTags()
		<using test initialization context> <using test initialization context> <using test initialization context>
		['ghi', 'abc', 'def', 'all']
		"""
		taglist = getStringList(list(tags))
		self.__tags = taglist + self.__tags
		assert sorted(list(set(self.__tags))) == sorted(list(self.__tags)) # check for duplicates
		init = getBuildInitializationContext()
		if init: init.registerTags(self, taglist) # init will be None during doctests
		return self

	def priority(self, pri):
		"""
		Set the priority of this target it encourage it (and its deps) to be 
		built earlier in the process. The default priority is 0.0

		pri -- a float representing the priority. Higher numbers will be built
			first where possible.
		"""
		self.__priority = pri
		return self
	
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

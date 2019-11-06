# xpyBuild - eXtensible Python-based Build System
#
# Support for defining properties of various types, for use by build files. 
# Assumes the buildLoader global variable has been set
#
# Copyright (c) 2013 - 2017, 2019 Software AG, Darmstadt, Germany and/or its licensors
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
# $Id: propertysupport.py 301527 2017-02-06 15:31:43Z matj $
#

import os
import re
import logging
import mimetypes
__log = logging.getLogger('propertysupport') # cannot call it log cos this gets imported a lot

from xpybuild.buildcommon import *
from xpybuild.buildcontext import BuildInitializationContext, getBuildInitializationContext # getBuildInitializationContext is here for compatibility only
from xpybuild.utils.fileutils import parsePropertiesFile
from xpybuild.utils.buildfilelocation import BuildFileLocation, formatFileLocation
from xpybuild.buildexceptions import BuildException

# All the public methods that build authors are expected to use to interact with properties and options

def defineOption(name, default):
	""" Define an option with a default (can be overridden globally using setGlobalOption() or on individual targets).
	
	This method is typically used only when implementing a new kind of target. 
	
	Options are not available for ${...} expansion (like properties), but 
	rather as used for (optionally inheritably) settings that affect the 
	behaviour of one or more targets. They are accessed using self.options 
	in any target instance. 
	
	@param name: The option name, which should usually be in lowerCamelCase, with 
	a TitleCase prefix specific to this target or group of targets, often 
	matching the target name, e.g. "Javac.compilerArgs". 

	@param default: The default value of the option
	"""
	init = BuildInitializationContext.getBuildInitializationContext()
	if init:
		init._defineOption(name, default)
	elif 'doctest' not in sys.argv[0] and 'sphinx' not in sys.argv[0]:
		# this check is so we notice if unfortunate module order causes us to try to 
		# define options before we have a real context to put them in
		assert False, 'Cannot define options at this point in the build as there is no initialization build context active'

def setGlobalOption(key, value):
	"""
		Globally override the default for an option
	"""
	init = BuildInitializationContext.getBuildInitializationContext()
	if init:
		init.setGlobalOption(key, value)


def defineStringProperty(name, default):
	""" Define a string property which can be used in ${...} substitution. 
	
	Do not use this generic function for any properties representing a file 
	system path, or a boolean/enumeration. 
	
	@param name: The property name

	@param default: The default value of the propert (can contain other ${...} variables)
	If set to None, the property must be set on the command line each time
	"""
	init = BuildInitializationContext.getBuildInitializationContext()
	if init: init.defineProperty(name, default, lambda v: BuildInitializationContext.getBuildInitializationContext().expandPropertyValues(v))

def definePathProperty(name, default, mustExist=False):
	""" Define a property that corresponds to a path.

	Path is normalized and any trailing slashes are removed. An error is raised 
	if the path does not exist when the property is defined if mustExist=True. 
	
	Paths are always absolutized.
	
	For paths which represent output directories of this build, call 
	registerOutputDirProperties afterwards. 

	@param name: The name of the property

	@param default: The default path value of the property (can contain other ${...} variables). 
	If a relative path, will be resolved relative to the build file in 
	which it is defined. 
	If set to None, the property must be set on the command line each time

	@param mustExist: True if it's an error to specify a directory that doesn't
	exist (will raise a BuildException)
	
	"""

	# Expands properties, makes the path absolute, checks that it looks sensible and (if needed) whether the path exists
	def _coerceToValidValue(value):
		value = BuildInitializationContext.getBuildInitializationContext().expandPropertyValues(value)
		
		if not os.path.isabs(value):
			# must absolutize this, as otherwise it might be used from a build 
			# file in a different location, resulting in the same property 
			# resolving to different effective values in different places
			value = BuildFileLocation(raiseOnError=True).buildDir+'/'+value
		
		value = normpath(value).rstrip('/\\')
		if mustExist and not os.path.exists(value):
			raise BuildException('Invalid path property value for "%s" - path "%s" does not exist' % (name, value))
		return value
		
	init = BuildInitializationContext.getBuildInitializationContext()
	if init: init.defineProperty(name, default, coerceToValidValue=_coerceToValidValue)


def defineOutputDirProperty(name, default):
	""" Define a property that corresponds to a path that this build uses 
	as a destination for output files. Equivalent to calling definePathProperty 
	then registerOutputDirProperties.
	"""
	definePathProperty(name, default)
	registerOutputDirProperties(name)

def registerOutputDirProperties(*propertyNames):
	""" Registers the specified path property name(s) as being an output directory 
	of this build, meaning that they will be created automatically at the 
	beginning of the build process, and removed during a global clean.
	
	Typical usage is to call this just after definePathProperty. 
	"""
	init = BuildInitializationContext.getBuildInitializationContext()
	if init:
		for p in propertyNames:
			p = init.getPropertyValue(p)
			if not os.path.isabs(p): raise BuildException('Only absolute path properties can be used as output dirs: "%s"'%p)
			init.registerOutputDir(normpath(p)) 

def defineEnumerationProperty(name, default, enumValues):
	""" Defines a property that must take one of the specified values.

	@param name: The name of the property

	@param default: The default value of the property (can contain other ${...} variables)
	If set to None, the property must be set on the command line each time

	@param enumValues: A list of valid values for this property (can contain other ${...} variables)
	"""

	# Expands properties, then checks that it's one of the acceptible values
	def _coerceToValidValue(value):
		value = BuildInitializationContext.getBuildInitializationContext().expandPropertyValues(value)
		if value in enumValues: return value
		
		# case-insensitive match
		for e in enumValues:
			if e.lower()==value.lower():
				return e
			
		raise BuildException('Invalid property value for "%s" - value "%s" is not one of the allowed enumeration values: %s' % (name, value, enumValues))
		
	init = BuildInitializationContext.getBuildInitializationContext()
	if init:
		init.defineProperty(name, default, coerceToValidValue=_coerceToValidValue)
	
def defineBooleanProperty(name, default=False):
	""" Defines a boolean property that will have a True or False value. 
	
	@param name: The property name

	@param default: The default value (default = False)
	If set to None, the property must be set on the command line each time
	"""

	# Expands property values, then converts to a boolean
	def _coerceToValidValue(value):
		value = BuildInitializationContext.getBuildInitializationContext().expandPropertyValues(str(value))
		if value.lower() == 'true':
			return True
		if value.lower() == 'false' or value=='':
			return False
		raise BuildException('Invalid property value for "%s" - must be true or false' % (name))
	
	init = BuildInitializationContext.getBuildInitializationContext()
	if init:
		init.defineProperty(name, default, coerceToValidValue=_coerceToValidValue)

def definePropertiesFromFile(propertiesFile, prefix=None, excludeLines=None, conditions=None):
	"""
	Defines a set of properties from a .properties file
	
	@param propertiesFile: The file to include properties from (can include ${...} variables)

	@param prefix: if specified, this prefix will be added to the start of all property names from this file

	@param excludeLines: a string of list of strings to search for, any KEY containing these strings will be ignored
	
	@param conditions: an optional list of string conditions that can appear in property 
	keys e.g. "FOO<condition>=bar" where lines with no condition in this list 
	are ignored. Conditions are typically lowercase. 
	"""
	if conditions: assert not isinstance(conditions,str), 'conditions parameter must be a list'
	__log.info('Defining properties from file: %s', propertiesFile)
	context = BuildInitializationContext.getBuildInitializationContext()
	
	propertiesFile = context.getFullPath(propertiesFile, BuildFileLocation(raiseOnError=True).buildDir)
	try:
		f = open(propertiesFile, 'r') 
	except Exception as e:
		raise BuildException('Failed to open properties file "%s"'%(propertiesFile), causedBy=True)
	missingKeysFound = set()
	try:
		
		for key,value,lineNo in parsePropertiesFile(f, excludeLines=excludeLines):
			__log.debug('definePropertiesFromFile: expanding %s=%s', key, value)
			
			if '<' in key:
				c = re.search('<([^.]+)>', key)
				if not c:
					raise BuildException('Error processing properties file, malformed <condition> line at %s'%formatFileLocation(propertiesFile, lineNo), causedBy=True)
				key = key.replace('<'+c.group(1)+'>', '')
				if '<' in key: raise BuildException('Error processing properties file, malformed line with multiple <condition> items at %s'%formatFileLocation(propertiesFile, lineNo), causedBy=True)
				matches = True if conditions else False
				if matches:
					for cond in c.group(1).split(','):
						if cond.strip() not in conditions:
							matches = False
							break
				if not matches:
					__log.debug('definePropertiesFromFile ignoring line that does not match condition: %s'%key)
					missingKeysFound.add(key)
					continue
				else:
					missingKeysFound.discard(key) # optimization to keep this list small
			
			if prefix: key = prefix+key 
			# TODO: make this work better by allowing props to be expanded using a local set of props from this file in addition to build props
			
			try:
				value = context.expandPropertyValues(value)
				context.defineProperty(key, value, debug=True)
			except BuildException as e:
				raise BuildException('Error processing properties file %s'%formatFileLocation(propertiesFile, lineNo), causedBy=True)
	finally:
		f.close()
	
	# ensure there the same set of properties is always defined regardless of conditions - 
	# otherwise it's easy for typos or latent bugs to creep in
	for k in missingKeysFound:
		try:
			context.getPropertyValue(k)
		except BuildException as e:
			raise BuildException('Error processing properties file %s: no property key found for "%s" matched any of the conditions: %s'%(
				propertiesFile, k, conditions), causedBy=False)

def getPropertyValue(propertyName):
	""" Return the current value of the given property (can only be used during build file parsing).
	
	For Boolean properties this will be a python Boolean, for everything else it will be a string. 
	"""
	context = BuildInitializationContext.getBuildInitializationContext()
	assert context, 'getProperty can only be used during build file initialization phase'
	return context.getPropertyValue(propertyName)

def getProperty(propertyName):
	""" Deprecated name; for consistency, use getPropertyValue instead. 
	
	@deprecated: use getPropertyValue instead. 
	"""
	return getPropertyValue(propertyName)

def expandListProperty(propertyName):
	""" Utility method for use during property and target definition 
	that returns a list containing the values of the specified 
	list property. 
	
	This is useful for quickly defining multiple targets (e.g. file copies) 
	based on a list defined as a property. 
	
	@param propertyName: must end with [] e.g. 'MY_JARS[]'
	
	"""
	assert not propertyName.startswith('$')
	assert propertyName.endswith('[]')
	context = BuildInitializationContext.getBuildInitializationContext()

	# although this isn't a valid return value, it's best to avoid triggering the assertion 
	# below to support doc-testing custom xpybuild files that happen to use this method
	if (not context) and 'doctest' in sys.argv[0]: return ['${%s}'%propertyName]

	assert context, 'expandListProperty utility can only be used during build file initialization phase'
	return context.expandListPropertyValue(propertyName)

def enableEnvironmentPropertyOverrides(prefix):
	"""
	Turns on support for value overrides for defined properties from the 
	environment as well as from the command line. 
	
	Allows any property value to be overridden from an environment variable, 
	provided the env var begins with the specified prefix. 
	
	This setting only affects properties defined after the point in the 
	build files where it is called. 
	
	Property values specified on the command line take precedence over env 
	vars, which in turn take precedence over the defaults specified when 
	properties are defined. 
	
	@param prefix: The prefix added to the start of a build property name to form 
	the name of the environment variable; the prefix is stripped from the 
	env var name before it is compared with properties defined by the build. This is mandatory (cannot be 
	empty) and should be set to a build-specific string (e.g. "XYZ_") in 
	order to ensure that there is no chance of build properties being 
	accidentally overridden. (e.g. many users have JAVA_HOME in their env 
	but also in their build, however it may be important for them to 
	have different values, and subtle bugs could result if the build 
	property was able to be set implicitly from the environment).
	"""
	init = BuildInitializationContext.getBuildInitializationContext()
	if init:
		init.enableEnvironmentPropertyOverrides(prefix)

class ExtensionBasedFileEncodingDecider:
	"""Can be used for the `common.fileEncodingDecider` option which decides what file encoding to use for 
	reading/writing a text file given its path. 
	
	The decider option is called with arguments: (context, path), and returns the name of the encoding to be used for this path. 
	Additional keyword arguments may be passed to the decider in future. 
	
	This extension-based decider uses the specified dictionary of extensions to determine which 
	extension to use, including the special value L{ExtensionBasedFileEncodingDecider.BINARY} 
	which indicates non-text files. 

	"""
	
	BINARY = '<binary>'
	"""This constant should be used with ExtensionBasedFileEncodingDecider to indicate binary files that 
	should not be opened in text mode. """
	
	def __init__(self, extToEncoding={}, default=None): 
		"""
		@param defaultEncoding: The name of the default encoding to be used, another decider to delegate to, or None to defer to the configured global option. 
		Recommended values are: 'utf-8', 'ascii' or locale.getpreferredencoding().
		
		@param extToEncoding: A dictionary whose keys are extensions such as '.xml', '.foo.bar.baz' and values specify the encoding to use for each one, 
		or the constant L{ExtensionBasedFileEncodingDecider.BINARY} which indicates a non-text file (not all targets support binary). 
		The extensions can contain ${...} properties. 
		"""
		self.extToEncodingDict, self.defaultEncoding = dict(extToEncoding), default
		# enforce starts with a . to prevent mistakes and allow us to potentially optimize the implementation in future
		for k in extToEncoding: 
			if not k.startswith('.'): raise BuildException(f'ExtensionBasedFileEncodingDecider extension does not start with the required "." character: "{k}"')
		self.__cache = None,None
		self.__stringified = f'ExtensionBasedFileEncodingDecider({self.extToEncodingDict}; default={self.defaultEncoding})'
		
	def __repr__(self): return self.__stringified
	def __call__(self, context, path, **forfutureuse):
		(cachecontext, cache) = self.__cache # single field access - probably sufficiently thread-safe given how the GIL works
		
		if cachecontext != context:
			# (re)build the cache if it doesn't already exist, or if for some unexpected reason the context has changed
			cache = {}
			for ext, enc in self.extToEncodingDict.items():
				cache[context.expandPropertyValues(ext)] = enc or self.defaultEncoding
			self.cache = (context, cache)
		
		p = os.path.basename(path).split('.')
		for i in range(1, len(p)): # in case it has an .x.y multi-part extension
			result = cache.get('.' + '.'.join(p[i:]), None)
			if result is not None: return result
		
		if self.defaultEncoding is not None: 
			# could be another decider, so call it
			if callable(self.defaultEncoding): return self.defaultEncoding(context, path, **forfutureuse)
			assert isinstance(self.defaultEncoding, str), 'Encoding must be a str (or callable): '+repr(self.defaultEncoding)
			return self.defaultEncoding
		
		fallbackDecider = context.getGlobalOption('common.fileEncodingDecider')
		if fallbackDecider is not self: return fallbackDecider(context, path, **forfutureuse)
		raise Exception(f'File encoding decider cannot handle path \'{path}\': {self}')
	
	@staticmethod
	def getDefaultFileEncodingDecider():
		""" Creates the file encoding decider that is used by default if per-target 
		or global option is specified. 
		
		Currently this supports utf-8 encoding of json/xml/yaml/yml files, 
		and binary for common non-application/text mime types such as image files 
		(based on the mime settings of the current machine). 
		
		Additional types may be added to this in future releases, so you should 
		use `setGlobalOption('common.fileEncodingDecider', ...)` if you wish to control 
		the encodings precisely and ensure identical behaviour across machines.

		"""
		d = {
			'.json':'utf-8',
			'.xml':'utf-8',
			'.yaml':'utf-8', '.yml':'utf-8',
		}
		# add binary for known non-text types such as images. Don't do it for application/ as that includes 
		# text formats such as js and json
		for (ext,contenttype) in sorted(mimetypes.types_map.items()):
			if not contenttype.startswith(('text/', 'application/')):
				d[ext] = ExtensionBasedFileEncodingDecider.BINARY
		return ExtensionBasedFileEncodingDecider(d, default='ascii')

import pkgutil

def enableLegacyXpybuildModuleNames():
	"""
	Adds aliases for pre-3.0 module names e.g. `buildcommon` instead of `xpybuild.buildcommon`, etc. 
	
	The old names are deprecated, so this should be used only as a temporary measure. 
	"""
	# must manually import every single module from 'utils' and 'targets'; 
	# although just importing 'utils' appears to work, 
	# we end up with duplicate packages for the modules underneath it 
	# (and so may attempt to import and hence define the same option twice)
	import xpybuild.utils
	import xpybuild.targets
	for parentpackage in [xpybuild, xpybuild.utils, xpybuild.targets]:
		for _, modulename, ispkg in pkgutil.iter_modules(
				path=parentpackage.__path__, prefix=(parentpackage.__name__[len('xpybuild.'):]+'.').lstrip('.')):
			__log.debug('enableLegacyXpybuildModuleNames: Importing legacy package name %s', modulename)
			if modulename!='propertysupport': # first make sure the original one has been imported
				exec(f'import xpybuild.{modulename}', {})
			# then define an alias
			exec(f'sys.modules["{modulename}"] = sys.modules["xpybuild.{modulename}"]')
	assert 'utils.fileutils' in sys.modules, sys.modules # sanity check that it worked
	assert 'targets.copy' in sys.modules, sys.modules # sanity check that it worked

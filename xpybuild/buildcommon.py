# xpyBuild - eXtensible Python-based Build System
#
# This module holds definitions that are used throughout the build system, and 
# typically all names from this module will be imported. 
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
# $Id: buildcommon.py 301527 2017-02-06 15:31:43Z matj $
#

"""
Contains standard functionality for use in build files such as `xpybuild.buildcommon.include`, useful constants such as `xpybuild.buildcommon.IS_WINDOWS` and 
functionality for adding prefixes/suffixes to paths such as `xpybuild.buildcommon.FilenameStringFormatter`. 
"""

import traceback, os, sys, locale, inspect, io
import re
import platform

import logging
# do NOT define a 'log' variable here or targets will use it by mistake

def __getXpybuildVersion():

	try:
		with open(os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))), "XPYBUILD_VERSION")) as f:
			return f.read().strip()
	except Exception:
		raise
		return "<unknown>"
XPYBUILD_VERSION: str = __getXpybuildVersion()
"""The current xpybuild version."""


def include(file):
	""" Parse and register the targets and properties in in the specified 
	``XXX.xpybuild.py`` file. 
	
	Targets should only be defined in files included using this method, 
	not using python import statements. 
	
	@param file: a path relative to the directory containing this file. 
	"""

	from xpybuild.buildcontext import getBuildInitializationContext
	from xpybuild.utils.buildfilelocation import BuildFileLocation

	file = getBuildInitializationContext().expandPropertyValues(file)

	assert file.endswith('.xpybuild.py') # enforce recommended naming convention
	
	filepath = getBuildInitializationContext().getFullPath(file, os.path.dirname(BuildFileLocation._currentBuildFile[-1]))
	
	BuildFileLocation._currentBuildFile.append(filepath) # add to stack of files being parsed
	
	namespace = {}
	exec(compile(open(filepath, "rb").read(), filepath, 'exec'), namespace, namespace)
	
	del BuildFileLocation._currentBuildFile[-1]
	
	return namespace

IS_WINDOWS: bool = platform.system()=='Windows'
""" A boolean that specifies whether this is Windows or some other operating system. """
# (we won't want constants for every possible OS here, but since there is so much conditionalization between 
# windows and unix-based systems, much of it on the critical path, it is worthwhile having a constant for this). 

if IS_WINDOWS:
	def isWindows():
		""" Returns True if this is a windows platform. 
		
		@deprecated: Use the `IS_WINDOWS` constant instead. 
		"""
		return True
else:
	def isWindows():
		""" Returns True if this is a windows platform. 
		
		@deprecated: Use the `IS_WINDOWS` constant instead. 
		"""
		return False

def defineAtomicTargetGroup(*targets):
	""" The given targets must all be built before anything which depends on any of those targets.
	
	Returns the flattened list of targets. 
	"""
	
	from xpybuild.buildcontext import getBuildInitializationContext
	targets = flatten(targets)
	getBuildInitializationContext().defineAtomicTargetGroup(targets)
	return targets

def requireXpybuildVersion(version: str):
	""" Checks that this xpybuild is at least a certain version number. """
	from xpybuild.utils.stringutils import compareVersions
	if compareVersions(XPYBUILD_VERSION, version) < 0: raise Exception("This build file requires xpyBuild at least version "+version+" but this is xpyBuild "+XPYBUILD_VERSION)

requireXpyBuildVersion = requireXpybuildVersion
""" 
.. private:: Old name for compatibility. 

Use requireXpyBuildVersion instead.
"""

def registerPreBuildCheck(fn):
	""" Defines a check which will be called after any clean but before any build actions take place.
	    fn should be a functor that takes a context and raises a BuildException if the check fails. """
	from buildcontext import getBuildInitializationContext
	getBuildInitializationContext().registerPreBuildCheck(fn)

class StringFormatter(object):
	""" A simple named functor for applying a ``%s``-style string format, useful 
	in situations where a function is needed to add a suffix/prefix for the 
	value of an option. 
	"""
	def __init__(self, formatstring):
		self.fmt = formatstring
	def __repr__(self):
		return 'StringFormatter<"%s">'%self.fmt
	def __call__(self, *args, **kwargs):
		assert not kwargs
		assert len(args)==1
		return self.fmt % args[0]
	
class FilenameStringFormatter(object):
	""" A simple named functor for applying a ``%s``-style string format. 
		 Formatter is just applied to the basename part of the filename,
		 the dirname part is preserved as-is.
	"""
	def __init__(self, formatstring):
		self.fmt = formatstring
	def __repr__(self):
		return 'FilenameStringFormatter<"%s">'%self.fmt
	def __call__(self, *args, **kwargs):
		assert not kwargs
		assert len(args)==1
		return os.path.join(os.path.dirname(args[0]), self.fmt % os.path.basename(args[0]))

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
	__log = logging.getLogger('xpybuild.buildcommon')
	for parentpackage in [xpybuild, xpybuild.utils, xpybuild.targets]:
		for _, modulename, ispkg in pkgutil.iter_modules(
				path=parentpackage.__path__, prefix=(parentpackage.__name__[len('xpybuild.'):]+'.').lstrip('.')):
			__log.debug('enableLegacyXpybuildModuleNames: Importing legacy package name %s', modulename)
			if modulename!='buildcommon': # first make sure the original one has been imported
				exec(f'import xpybuild.{modulename}', {})
			# then define an alias
			exec(f'sys.modules["{modulename}"] = sys.modules["xpybuild.{modulename}"]')
	assert 'utils.fileutils' in sys.modules, sys.modules # sanity check that it worked
	assert 'targets.copy' in sys.modules, sys.modules # sanity check that it worked

	# aliases for modules we folded into other modules in v3.0, or moved
	exec(f'sys.modules["propertyfunctors"] = sys.modules["xpybuild.propertysupport"]')
	exec(f'sys.modules["buildexceptions"] = sys.modules["xpybuild.utils.buildexceptions"]')

	xpybuild.targets.touch = sys.modules["xpybuild.targets.writefile"]
	exec(f'sys.modules["targets.touch"] = sys.modules["xpybuild.targets.writefile"]')

	xpybuild.targets.unpack = sys.modules["xpybuild.targets.archive"]
	exec(f'sys.modules["targets.unpack"] = sys.modules["xpybuild.targets.archive"]')
	xpybuild.targets.zip = sys.modules["xpybuild.targets.archive"]
	exec(f'sys.modules["targets.zip"] = sys.modules["xpybuild.targets.archive"]')
	xpybuild.targets.tar = sys.modules["xpybuild.targets.archive"]
	exec(f'sys.modules["targets.tar"] = sys.modules["xpybuild.targets.archive"]')

import xpybuild.utils.fileutils
from xpybuild.utils.flatten import flatten

isDirPath = xpybuild.utils.fileutils.isDirPath
"""Returns true if the path is a directory (ends with a slash, ``/`` or ``\\\\``). """

normpath = xpybuild.utils.fileutils.normPath
"""
.. private:: This is deprecated in favour of fileutils.normPath and hidden from documentation to avoid polluting the docs. 

"""

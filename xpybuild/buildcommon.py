# xpyBuild - eXtensible Python-based Build System
#
# This module holds definitions that are used throughout the build system, and 
# typically all names from this module will be imported. 
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
# $Id: buildcommon.py 301527 2017-02-06 15:31:43Z matj $
#

import traceback, os, sys, locale, inspect, io
import re
import platform

import logging
# do NOT define a 'log' variable here or targets will use it by mistake

from utils.flatten import flatten
import utils.fileutils
from utils.fileutils import parsePropertiesFile

def __getXpybuildVersion():

	try:
		with open(os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))), "XPYBUILD_VERSION")) as f:
			return f.read().strip()
	except Exception:
		raise
		return "<unknown>"
_XPYBUILD_VERSION = __getXpybuildVersion()



def include(file):
	""" Parse and register the targets and properties in in the specified 
	xpybuild.py file. 
	
	Targets should only be defined in files included using this method, 
	not using python import statements. 
	
	@param file: a path relative to the directory containing this file. 
	"""

	from buildcontext import getBuildInitializationContext
	from utils.buildfilelocation import BuildFileLocation

	file = getBuildInitializationContext().expandPropertyValues(file)

	assert file.endswith('.xpybuild.py') # enforce recommended naming convention
	
	filepath = getBuildInitializationContext().getFullPath(file, os.path.dirname(BuildFileLocation._currentBuildFile[-1]))
	
	BuildFileLocation._currentBuildFile.append(filepath) # add to stack of files being parsed
	
	namespace = {}
	exec(compile(open(filepath, "rb").read(), filepath, 'exec'), namespace, namespace)
	
	del BuildFileLocation._currentBuildFile[-1]
	
	return namespace


def compareVersions(v1, v2):
	""" Compares two alphanumeric dotted version strings to see which is more recent. 

		Example usage::
		
			if self.compareVersions(thisversion, '1.2.alpha-3') > 0:
				... # thisversion is newer than 1.2.alpha-3 

		The comparison algorithm ignores case, and normalizes separators ./-/_ 
		so that `'1.alpha2'=='1Alpha2'`. Any string components are compared 
		lexicographically with other strings, and compared to numbers 
		strings are always considered greater. 

		@param v1: A string containing a version number, with any number of components. 
		@param v2: A string containing a version number, with any number of components. 

		@return: an integer > 0 if v1>v2, 
		an integer < 0 if v1<v2, 
		or 0 if they are semantically the same.

		>>> compareVersions('10-alpha5.dev10', '10alpha-5-dEv_10') == 0 # normalization of case and separators
		True

		>>> compareVersions('1.2.0', '1.2')
		0

		>>> compareVersions('1.02', '1.2')
		0

		>>> compareVersions('1.2.3', '1.2') > 0
		True

		>>> compareVersions('1.2', '1.2.3')
		-1
		
		>>> compareVersions('10.2', '1.2')
		1

		>>> compareVersions('1.2.text', '1.2.0') # letters are > numbers
		1

		>>> compareVersions('1.2.text', '1.2') # letters are > numbers 
		1

		>>> compareVersions('10.2alpha1', '10.2alpha')
		1

		>>> compareVersions('10.2dev', '10.2alpha') # letters are compared lexicographically
		1

		>>> compareVersions('', '')
		0

		>>> compareVersions('1', '')
		1
	"""
	
	def normversion(v):
		# normalize versions into a list of components, with integers for the numeric bits
		v = [int(x) if x.isdigit() else x for x in re.split('([0-9]+|[.])', v.lower().replace('-','.').replace('_','.')) if (x and x != '.') ]
		return v
	
	v1 = normversion(v1)
	v2 = normversion(v2)
	
	# make them the same length
	while len(v1)<len(v2): v1.append(0)
	while len(v1)>len(v2): v2.append(0)

	for i in range(len(v1)):
		if type(v1[i]) != type(v2[i]): # can't use > on different types
			if type(v2[i])==int: # define string>int
				return +1
			else:
				return -1
		else:
			if v1[i] > v2[i]: return 1
			if v1[i] < v2[i]: return -1
	return 0


def requireXpyBuildVersion(version: str):
	""" Checks that this xpybuild is at least a certain version number """
	if compareVersions(_XPYBUILD_VERSION, version) < 0: raise Exception("This build file requires xpyBuild at least version "+version+" but this is xpyBuild "+_XPYBUILD_VERSION)

isDirPath = utils.fileutils.isDirPath
""" Returns true if the path is a directory (ends with / or \\). """

def normpath(path):
	""" Normalizes the specified file or dir path to remove ".." sequences and 
	differences in the capitalization of Windows drive letters. 
	
	Does not add Windows long-path safety or absolutization. 
	
	Leaves in place any  trailing platform-appropriate character to indicate 
	directory if appropriate.
	
	See also L{utils.fileutils.normLongPath} and L{utils.fileutils.toLongPathSafe}. 

	"""
	path = os.path.normpath(path)+(os.path.sep if isDirPath(path) else '')
	
	# normpath does nothing to normalize case, and windows seems to be quite random about upper/lower case 
	# for drive letters (more so than directory names), with different cmd prompts frequently using different 
	# capitalization, so normalize at least that bit, to prevent spurious rebuilding from different prompts
	if len(path)>2 and IS_WINDOWS and path[1] == ':': 
		path = path[0].lower()+path[1:]
			
	return path

""" A boolean that specifies whether this is Windows or some other operating system. """
IS_WINDOWS = platform.system()=='Windows'
# (we won't want constants for every possible OS here, but since there is so much conditionalization between 
# windows and unix-based systems, much of it on the critical path, it is worthwhile having a constant for this). 

if IS_WINDOWS:
	def isWindows():
		""" Returns True if this is a windows platform. 
		@deprecated: Use the IS_WINDOWS constant instead. 
		"""
		return True
else:
	def isWindows():
		""" Returns True if this is a windows platform. 
		@deprecated: Use the IS_WINDOWS constant instead. 
		"""
		return False

_stdoutEncoding = None
try:
	_stdoutEncoding = sys.stdout.encoding or locale.getpreferredencoding() # stdout encoding will be None unless in a terminal
except:
	pass # probably in epydoc

def getStdoutEncoding(): 
	""" Returns the most likely encoding used by subprocesses, based on 
	whether the build is running in a console, etc 
	which is typically what should be used for converting byte strings from 
	subprocesses to python unicode.
	"""
	return _stdoutEncoding

def formatFileLocation(path, lineNumber): 
	""" A functor to format a file and a line number for output. """
	# use format vim uses for opening file at line number; easy enough to convert to ultra edit path/linenumber syntax
	return '"%s" +%d' % (os.path.normpath(path), lineNumber)

def defineAtomicTargetGroup(*targets):
	""" The given targets must all be built before anything which depends on any of those targets.
	
	Returns the flattened list of targets. 
	"""
	
	from buildcontext import getBuildInitializationContext
	targets = flatten(targets)
	getBuildInitializationContext().defineAtomicTargetGroup(targets)
	return targets

def registerPreBuildCheck(fn):
	""" Defines a check which will be called after any clean but before any build actions take place.
	    fn should be a functor that takes a context and raises a BuildException if the check fails. """
	from buildcontext import getBuildInitializationContext
	getBuildInitializationContext().registerPreBuildCheck(fn)

class StringFormatter(object):
	""" A simple named functor for applying a %s-style string format, useful 
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
	""" A simple named functor for applying a %s-style string format. 
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
	
	

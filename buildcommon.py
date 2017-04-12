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

import traceback, os, sys, locale, inspect


import platform

import logging
# do NOT define a 'log' variable here or targets will use it by mistake

from utils.flatten import flatten
from utils.fileutils import parsePropertiesFile

def __getXpybuildVersion():

	try:
		with open(os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))), "release.properties")) as f:
			_RELEASE_PROPERTIES=parsePropertiesFile(f)
	
		return [value for (key, value, line) in _RELEASE_PROPERTIES if key == "VERSION"][0]
	except Exception:
		raise
		return "<unknown>"
_XPYBUILD_VERSION = __getXpybuildVersion()



def include(file):
	""" Parse and register the targets and properties in in the specified 
	xpybuild.py file. 
	
	file: a path relative to the directory containing this file. 
	"""

	from buildcontext import getBuildInitializationContext
	from utils.buildfilelocation import BuildFileLocation

	file = getBuildInitializationContext().expandPropertyValues(file)

	assert file.endswith('.xpybuild.py') # enforce recommended naming convention
	
	# maybe use getFullPath here?
	filepath = os.path.abspath(os.path.join(BuildFileLocation(raiseOnError=True).buildDir, file))
	
	namespace = {}
	execfile(filepath, namespace, namespace)
	return namespace

def _compareVersion(version, ref):
	""" returns true if version >= ref """
	version = version.split('.')
	ref = ref.split('.')
	equal = True
	for i in range(0, min(len(version), len(ref))):
		if int(version[i]) < int(ref[i]):
			return False
		elif version[i] != ref[i]:
			equal = False
	return len(version) >= len(ref) if equal else True

def requireXpyBuildVersion(version):
	""" Checks that this xpybuild is at least a certain version number """
	if not _compareVersion(_XPYBUILD_VERSION, version): raise Exception("This build file requires xpyBuild at least version "+version+" but this is xpyBuild "+_XPYBUILD_VERSION)


def isDirPath(path):
	""" Returns true if the path is a directory (ends with / or \\). """
	return path and (path.endswith('/') or path.endswith('\\'))

def normpath(path):
	""" Normalizes the specified file or dir path, leaving in place a 
	trailing platform-appropriate character to indicate directory if appropriate.

	"""
	if isinstance(path, unicode) and not (isWindows() and path.startswith('\\\\?')):
		path = path.encode()
	path = os.path.normpath(path)+(os.path.sep if isDirPath(path) else '')
	
	# normpath does nothing to normalize case, and windows seems to be quite random about upper/lower case 
	# for drive letters (more so than directory names), with different cmd prompts frequently using different 
	# capitalization, so normalize at least that bit, to prevent spurious rebuilding from different prompts
	if len(path)>2 and isWindows() and path[1] == ':': 
		path = path[0].lower()+path[1:]
			
	return path
	
def isWindows():
	""" Returns True if this is a windows platform. """
	return platform.system()=='Windows'

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
	
	

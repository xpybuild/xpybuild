# buildfilelocation - Class for getting and holding info on the filename and 
# line of a build file elemnet
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
# $Id: buildfilelocation.py 301527 2017-02-06 15:31:43Z matj $
#

import traceback, inspect, os, sys

class BuildFileLocation(object):
	""" Represents information about a location in the user's build file.
	"""
	buildFile = None
	buildDir = None
	lineNumber = None
	#sourceLine = None
	
	_currentBuildFile = [] # for internal use only; last item indicates the file currently being parsed
	
	def __init__(self, raiseOnError=False):
		"""
		Constructs a new instance by inspecting the stack to find what part 
		of the build file we're currently processing. 
		
		This should only be used during the parsing phase, an empty location 
		will be returned if this is called while building or dependency 
		checking a target. 
		
		@param raiseOnError: if False, creates a BuildFileLocation with None for 
		the buildFile/buildDir if we are not currently parsing any included 
		build files. 
		"""
		if BuildFileLocation._currentBuildFile:
			x = self._getCorrectFrame() 
		else:
			# do not even try to get location if not doing parsing, since in 
			# almost all cases the location of the current thread's target 
			# is more useful
			x = None 
		
		if x != None:
			filename, lineno = x
			self.buildFile = filename
			self.buildDir = os.path.dirname(filename)
			if 'doctest' in sys.argv[0]: self.buildDir = 'BUILD_DIR'
			self.lineNumber = lineno
		else:
			if 'doctest' in sys.argv[0]: 
				self.buildDir = 'BUILD_DIR'
			if raiseOnError:
				raise Exception('Cannot find the location in source build file')
	
	def __str__(self):
		if self.buildFile: return formatFileLocation(self.buildFile, self.lineNumber)
		return '<unknown build file location>'
		
	def getLineString(self):
		#if self.sourceLine:
		#	return '%s: %s' % (self.__str__(), self.sourceLine)
		#else:
		return self.__str__()
	
	def _getCorrectFrame(self):
		context = 3
		frame = sys._getframe(1)
		# nb: this can be very expensive so we try to do the absolute bare minimum of work here
		while frame:
			filename = inspect.getfile(frame)
			assert filename
			if filename.endswith('.pyc'): filename = filename[:-3]+'.py'
				
			# perform some cross-OS but low cost (no disk access) canonicalization
			# of the paths
			if filename.lower().replace('\\','/') == BuildFileLocation._currentBuildFile[-1].lower().replace('\\','/'):
				lineno = inspect.getlineno(frame)
				return filename, lineno
				
			frame = frame.f_back

# down here to avoid circular reference
from buildcommon import formatFileLocation

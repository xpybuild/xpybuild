# exceptions - Holds the main exception(s) used by build targets
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
# $Id: buildexceptions.py 301527 2017-02-06 15:31:43Z matj $
#

import traceback, os, sys

from utils.buildfilelocation import BuildFileLocation


class BuildException(Exception):
	""" A BuildException represents an error caused by an incorrect build or a runtime build problem. i.e. anything 
	that isn't an internal xpybuild error.
	
	""" 
	
	def __init__(self, message, location=None, causedBy=False):
		""" 
		BuildExceptions thrown during loading of the build config files will include the build file location 
		(from their call stack) in the message. BuildExceptions thrown during operations on a target 
		(dep resolution, execution, cleaning) will have information about that target added by xpybuild 
		when it is logged, so there is usually no reason to explicitly add the target name into the message. 
		
		The location can optionally be specified explicitly (e.g. for pathsets with delayed evaluation). 
	
		@param message: the error cause (does not need to include the target name)
		@param location: usually None, or else a BuildFileLocation object for the source line that caused the problem
		@param causedBy: if True, takes the exception currently on the stack as the caused of this exception, and 
		adds it to the build exception message
		"""
		assert message
		self.__msg = message.strip()
		
		if not location: location = BuildFileLocation(raiseOnError=False)
		self.__location = location
		
		if causedBy == True:
			causedBy = sys.exc_info()
			
			causedByMsg = causedBy[1].__msg if isinstance(causedBy[1], BuildException) else '%s'%(causedBy[1])
			if (causedByMsg not in self.__msg): self.__msg += (': %s'%causedByMsg)
			self.__causedByTraceback = traceback.format_exc(causedBy)
		else: 
			assert causedBy==False
			self.__causedByTraceback = None
	
	def getLoggerExtraArgDict(self, target=None):
		"""
		Returns a dict suitable for passing as extra= in a logger call, to set 
		filename/lineno location information if available. 
		
		@param target: optionally used to find location if not available in this exception
		"""
		if self.__location.buildFile:
			return {'xpybuild_filename':self.__location.buildFile, 'xpybuild_line':self.__location.lineNumber }
		if target and target.location.buildFile:
			return {'xpybuild_filename':target.location.buildFile, 'xpybuild_line':target.location.lineNumber }
		return {}
	
	def __repr__(self): 
		""" Return the type of the exception and the message on a single line"""
		# don't know the target, so this isn't very useful, therefore discourage use by making it look scary
		return 'BuildException<%s>'%self.toSingleLineString(None) 
	def __str__(self): 
		""" Return the execption message on a single line """
		return self.toSingleLineString(None)

	def toSingleLineString(self, target):
		""" Return the exception message formatted to be a single line.

		Includes the build file location of the failed target if called with a target.

		@param target: The target causing the exception.
		"""
		# should be called with a target if possible
		result = self.__msg
		if target:
			result = '%s : %s'%(target, result)
		elif self.__location.buildFile and not str(self.__location) in result: # if we have a valid location, display that instead (unless it's already in a nested exception)
			result = '%s : %s'%(self.__location, result)
		return result

	def toMultiLineString(self, target, includeStack=False):
		""" Return the exception message, on multiple lines if neccessary, possibly including the stack trace.

		Includes the build file location of the failed target if called with a target.

		@param target: The target causing the exception.
		@param includeStack: If true, also includes the stack trace of the exception.
		"""
		# should be called with a target if possible
		result = self.__msg
		if target:
			result = '%s : %s'%(target, result)
		
		location = self.__location
		if target and not self.__location.buildFile: location = target.location
		if location.buildFile:
			result += '\n  %s'%location.getLineString()
			
		if self.__causedByTraceback and includeStack:
			result = result + '\n\nCaused by:\n%s'%(self.__causedByTraceback)
		return result.strip()

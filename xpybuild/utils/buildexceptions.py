# exceptions - Holds the main exception(s) used by build targets
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
# $Id: buildexceptions.py 301527 2017-02-06 15:31:43Z matj $
#

"""
The `xpybuild.utils.buildexceptions.BuildException` class used for (non-internal) problems encountered while building. 
"""

import traceback, os, sys

from xpybuild.utils.buildfilelocation import BuildFileLocation


class BuildException(Exception):
	""" A BuildException represents an error caused by an incorrect build or a runtime build problem. i.e. anything 
	that isn't an internal xpybuild error. 
	
	Typically a BuildException will not result in a python stack trace being 
	printed whereas other exception types will, so only raise one if you're 
	sure the message includes all required diagnostic information already. 
	
	""" 
	
	def __init__(self, message, location=None, causedBy=False):
		""" 
		BuildExceptions thrown during loading of the build config files will include the build file location 
		(from their call stack) in the message. BuildExceptions thrown during operations on a target 
		(dep resolution, execution, cleaning) will have information about that target added by xpybuild 
		when it is logged, so there is usually no reason to explicitly add the target name into the message. 
		
		To avoid losing essential diagnostic information, do not catch arbitrary 
		non-BuildException classes and wrap in a BuildException. 
		
		The location can optionally be specified explicitly (e.g. for pathsets with delayed evaluation). 
	
		@param message: the error cause (does not need to include the target name)
		
		@param location: usually None, or else a BuildFileLocation object for the source line that caused the problem. 
		This is useful if the build file location associated with the exception is 
		something other than a target, e.g. a PathSet. 
		
		@param causedBy: if True, takes the exception currently on the stack as the caused of this exception, and 
		adds it to the build exception message. If the cause is not a BuildException, then its stack 
		trace will be captured if this is True. 
		"""
		assert message
		self.__msg = message.strip()
		
		if causedBy:
			causedBy = sys.exc_info()
			causedByExc = causedBy[1]
			
			if isinstance(causedByExc, BuildException):
				causedByMsg = causedByExc.__msg
				if not location: location = causedByExc.__location
				self.__causedByTraceback = None # tracebacks not needed for BuildException, by definition
			else:
				causedByMsg = '%s'%causedByExc
				self.__causedByTraceback = ''.join(traceback.format_exception(*causedBy))
				
			if (causedByMsg not in self.__msg): self.__msg += (': %s'%causedByMsg)
			
		else: 
			assert causedBy==False
			self.__causedByTraceback = None

		# keep things simple by using None instead of an empty BuildFileLocation object
		if (not location or not location.buildFile) and BuildFileLocation._currentBuildFile:
			# only do this if we're parsing build files at the moment, otherwise it's 
			# more reliable to keep it blank and let the scheduler use the target's location
			location = BuildFileLocation(raiseOnError=False)
			if not location.buildFile: location = None
		self.__location = location
		
		Exception.__init__(self, self.__msg)
	
	def getLoggerExtraArgDict(self, target=None):
		"""
		Returns a dict suitable for passing as extra= in a logger call, to set 
		filename/lineno location information if available. 
		
		@param target: optionally used to find location if not available in this exception
		"""
		if self.__location:
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

		Includes the name of the failed target if called with a target.

		@param target: The target causing the exception.
		"""
		# should be called with a target if possible
		result = self.__msg
		
		# if we have a valid location, always display that (unless it's already in a nested exception)
		if self.__location and not str(self.__location) in result: 
			result = '%s : %s'%(self.__location, result)
		
		# if we have a target, always include it in the error
		if target:
			result = '%s : %s'%(target, result)
			
		return result

	def toMultiLineString(self, target, includeStack=False):
		""" Return the exception message, on multiple lines if necessary, possibly including the stack trace.

		If possible, includes the build file location associated with the 
		exception or with the failed target.

		@param target: The target causing the exception.
		@param includeStack: If true, also includes the stack trace of the exception.
		"""
		# should be called with a target if possible
		result = self.__msg
		if target:
			result = '%s : %s'%(target, result)
		
		location = self.__location
		if target and not self.__location: location = target.location
		if location:
			result += '\n  %s'%location.getLineString()
			
		if self.__causedByTraceback and includeStack:
			result = result + '\n\nCaused by:\n%s'%(self.__causedByTraceback)
		return result.strip()

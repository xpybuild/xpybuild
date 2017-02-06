# xpyBuild - eXtensible Python-based Build System
#
# Copyright (c) 2013 - 2017 Software AG, Darmstadt, Germany and/or its licensors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# $Id: writefile.py 301527 2017-02-06 15:31:43Z matj $
#

import os, re, stat

from buildcommon import *
from basetarget import BaseTarget
from utils.fileutils import mkdir, openForWrite, normLongPath

class WriteFile(BaseTarget):
	""" Target for writing out a textfile with hardcoded contents. 
	
	The file will only be updated if its contents have changed. 
	"""
	
	def __init__(self, name, getContents, dependencies=None, mode=None, executable=False, args=None, kwargs=None):
		"""
		name -- the output filename
		getContents -- a string (which will be subject to expansion) or 
			a function that accepts a context as input 
			followed optionally by any specified 'args') and returns 
			the string that should be written to the file. 	
			
			The file is written in binary mode, but any occurrences of \n in 
			the provided string will be replaced automatically with the 
			OS-specific line separator. 
			
			The function will be evaluated during the dependency resolution 
			phase. 
			
		mode -- unix permissions to set with chmod on the destination files. 
			If not specified, default mode is used. 
			Ignored on Windows platforms. 
		executable -- set to True to add Unix executable permissions (simpler 
			alternative to setting using mode)

		args -- optional tuple containing arguments that should be passed to 
			the getContents function, after the context argument (first arg)
		kwargs -- optional dictionary containing kwargs that should be passed 
			to the getContents function. 
		
		dependencies -- any targets which need to be built in order to run this
			target
		"""
		BaseTarget.__init__(self, name, dependencies or [])
		self.getContents = getContents
		self.__args = args or ()
		self.__kwargs = kwargs or {}
		self.__resolved = None
		self.__mode = mode
		self.__executable = executable 
	
	def getHashableImplicitInputs(self, context):
		""" The literal content text is considered the dependency of this target """
		return super(WriteFile, self).getHashableImplicitInputs(context) + [self._getContents(context)] + ['mode: %s, executable: %s'%(self.__mode, self.__executable)]
		
	def run(self, context):
		contents = self._getContents(context)
		
		mkdir(os.path.dirname(self.path))
		path = normLongPath(self.path)
		with openForWrite(path, 'wb') as f:
			f.write(contents.replace('\n', os.linesep))
		if self.__mode and not isWindows():
			os.chmod(path, self.__mode)
		if self.__executable and not isWindows():
			os.chmod(path, stat.S_IXOTH | stat.S_IXUSR | stat.S_IXGRP | os.stat(self.path).st_mode)
		
	def _getContents(self, context):
		if self.__resolved == None:
			c = self.getContents
			if isinstance(c, basestring) or hasattr(c, 'resolveToString'):
				self.__resolved = context.expandPropertyValues(c)
			else:
				self.__resolved = c(context, *self.__args, **self.__kwargs)
			assert isinstance(self.__resolved, basestring), 'WriteFile function must return a string: %r'%self.__resolved
		return self.__resolved

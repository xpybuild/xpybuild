# xpyBuild - eXtensible Python-based Build System
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
# $Id: symlink.py 301527 2017-02-06 15:31:43Z matj $
#

"""
Contains a target for creating a symbolic link. 
"""

import os

from xpybuild.buildcommon import *
from xpybuild.pathsets import *
from xpybuild.basetarget import BaseTarget
from xpybuild.utils.fileutils import mkdir

class SymLink(BaseTarget):
	""" Target for creating a file symbolic link (on supported platforms). 
	"""
	
	def __init__(self, dest, src, relative=True):
		"""
		dest: the link to be created
		src: what it points at
		"""
		if isinstance(dest, str) and dest.endswith('/'): raise BuildException('SymLink target can only be used for files, not directories') # for now
		if not hasattr(os, 'symlink'): raise BuildException('SymLink target is not supported on this platform')

		self.src = PathSet(src)
		self.relative=relative
		BaseTarget.__init__(self, dest, [self.src])
		# technically we don't need to depend on the contents of src at all, 
		# but in practice it might be useful to have other targets depending on the 
		# link in which case it's a good idea to recreate the link when the 
		# thing it points to is rebuild - and it's a very quick operation anyway
		self.tags('native')
	
	def run(self, context):
		mkdir(os.path.dirname(self.path))
		src = self.src.resolve(context)
		if len(src) != 1: raise BuildException('SymLink target "%s" is invalid - must have only only source path'%self.name)
		if src[0].endswith('/'): raise BuildException('SymLink target "%s" is invalid - must be a file not a directory'%self.name)

		os.symlink(src[0] if not self.relative else os.path.relpath(src[0], os.path.dirname(self.path)), self.path)

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
# $Id: tar.py 301527 2017-02-06 15:31:43Z matj $
#

import os, inspect, os.path
import time
import tarfile

from xpybuild.buildcommon import *
from xpybuild.pathsets import PathSet, BasePathSet
from xpybuild.basetarget import BaseTarget
from xpybuild.utils.fileutils import mkdir, deleteDir, normLongPath
from xpybuild.utils.flatten import flatten

class Tarball(BaseTarget):
	""" A target that creates a zip archive from a set of input files.
	"""

	def __init__(self, archive, inputs):
		"""
		archive: the archive to be created

		inputs: the files (usually pathsets) to be included in the archive.

		"""
		self.inputs = PathSet(inputs)
		BaseTarget.__init__(self, archive, self.inputs)

	def run(self, context):
		mkdir(os.path.dirname(self.path))
		with tarfile.open(normLongPath(self.path), 'w:gz') as output:
			for (f, o) in self.inputs.resolveWithDestinations(context):
				output.add(normLongPath(f).rstrip('/\\'), o)

	def getHashableImplicitInputs(self, context):
		# TODO: move to BaseTarget
		r = super(Tarball, self).getHashableImplicitInputs(context)
		
		# include source representation of deps list, so that changes to the list get reflected
		# this way of doing property expansion on the repr is a convenient 
		# shortcut (we want to expand property values to detect changes in 
		# versions etc that should trigger a rebuild, but just not do any 
		# globbing/searches here)
		r.append('src: '+context.expandPropertyValues(('%s'%self.inputs)))
		
		return r
	

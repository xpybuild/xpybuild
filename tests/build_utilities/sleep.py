# xpyBuild - eXtensible Python-based Build System
#
# Copyright (c) 2013 - 2018 Software AG, Darmstadt, Germany and/or its licensors
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
# $Id: touch.py 301527 2017-02-06 15:31:43Z matj $
#

import os, inspect

from buildcommon import *
from basetarget import BaseTarget

class Touch(BaseTarget):
	""" A target that creates an empty file
	"""
	
	def __init__(self, name):
		"""
		name: the output filename
		"""
		BaseTarget.__init__(self, name, [])
	
	def run(self, context):
		self.log.info("Touching %s", self.path)
		self.updateStampFile()

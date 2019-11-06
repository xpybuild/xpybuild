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

import os, inspect, time

from xpybuild.buildcommon import *
from xpybuild.basetarget import BaseTarget

class Sleep(BaseTarget):
	""" A target that creates an empty file
	"""
	
	def __init__(self, name, time, dependencies=None):
		"""
		name: the output filename
		time: the length of time to sleep (in seconds)
		"""
		BaseTarget.__init__(self, name, dependencies or [])
		self.time=float(time)
	
	def run(self, context):
		self.log.info("Sleeping for %s", self.time)
		time.sleep(self.time)
		self.log.info("Touching %s", self.path)
		self.updateStampFile()

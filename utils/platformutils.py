# platformutils - OS-specific utility functions
#
# Copyright (c) 2015 - 2017 Software AG, Darmstadt, Germany and/or its licensors
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
# $Id: platformutils.py 301527 2017-02-06 15:31:43Z matj $
#

import os, platform

import logging, buildcommon

def lowerCurrentProcessPriority():
	if buildcommon.isWindows():
		import win32process, win32api,win32con
		win32process.SetPriorityClass(win32api.GetCurrentProcess(), win32process.BELOW_NORMAL_PRIORITY_CLASS)
	else:
		# on unix, people may run nice before executing the process, so 
		# only change the priority unilaterally if it's currently at its 
		# default value
		if os.nice(0) == 0:
			os.nice(1) # change to 1 below the current level

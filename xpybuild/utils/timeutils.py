# timeutils - helper methods related to time
#
# Copyright (c) 2018 Software AG, Darmstadt, Germany and/or its licensors
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
# $Id$
#

import time

def formatTimePeriod(secs):
	"""
	Format a time period to a short display string. 	
	"""
	if secs >= 120:
		return '%0.1f minutes'%(secs/60.0)
	elif secs >= 10:
		return '%d seconds'%(secs)
	else:
		return '%0.1f seconds'%(secs)

# xpyBuild - eXtensible Python-based Build System
#
# This module holds definitions that are used throughout the build system, and 
# typically all names from this module will be imported. 
#
# Copyright (c) 2019 Software AG, Darmstadt, Germany and/or its licensors
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
# $Id: buildcommon.py 301527 2017-02-06 15:31:43Z matj $
#

""" Contains utility functions for manipulating strings, such as 
:obj:`compareVersions`. 

"""

import traceback, os, sys, io
import re
import platform
import logging

def compareVersions(v1, v2):
	""" Compares two alphanumeric dotted version strings to see which is more recent. 

		Example usage::
		
			if compareVersions(thisversion, '1.2.alpha-3') > 0:
				... # thisversion is newer than 1.2.alpha-3 

		The comparison algorithm ignores case, and normalizes separators ./-/_ 
		so that `'1.alpha2'=='1Alpha2'`. Any string components are compared 
		lexicographically with other strings, and compared to numbers 
		strings are always considered greater. 

		@param v1: A string containing a version number, with any number of components. 
		@param v2: A string containing a version number, with any number of components. 

		@return: an integer > 0 if v1>v2, 
		an integer < 0 if v1<v2, 
		or 0 if they are semantically the same.

		>>> compareVersions('10-alpha5.dev10', '10alpha-5-dEv_10') == 0 # normalization of case and separators
		True

		>>> compareVersions('1.2.0', '1.2')
		0

		>>> compareVersions('1.02', '1.2')
		0

		>>> compareVersions('1.2.3', '1.2') > 0
		True

		>>> compareVersions('1.2', '1.2.3')
		-1
		
		>>> compareVersions('10.2', '1.2')
		1

		>>> compareVersions('1.2.text', '1.2.0') # letters are > numbers
		1

		>>> compareVersions('1.2.text', '1.2') # letters are > numbers 
		1

		>>> compareVersions('10.2alpha1', '10.2alpha')
		1

		>>> compareVersions('10.2dev', '10.2alpha') # letters are compared lexicographically
		1

		>>> compareVersions('', '')
		0

		>>> compareVersions('1', '')
		1
	"""
	
	def normversion(v):
		# normalize versions into a list of components, with integers for the numeric bits
		v = [int(x) if x.isdigit() else x for x in re.split('([0-9]+|[.])', v.lower().replace('-','.').replace('_','.')) if (x and x != '.') ]
		return v
	
	v1 = normversion(v1)
	v2 = normversion(v2)
	
	# make them the same length
	while len(v1)<len(v2): v1.append(0)
	while len(v1)>len(v2): v2.append(0)

	for i in range(len(v1)):
		if type(v1[i]) != type(v2[i]): # can't use > on different types
			if type(v2[i])==int: # define string>int
				return +1
			else:
				return -1
		else:
			if v1[i] > v2[i]: return 1
			if v1[i] < v2[i]: return -1
	return 0


# flatten - take any input type and turn it sensibly into a list of strings (expansions, flattenning, function calls)
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
# $Id: flatten.py 301527 2017-02-06 15:31:43Z matj $
#

"""
Utility functions for normalizing and flattening deeply nested lists. 
"""

import types
import typing

def flatten(input) -> list:
	"""Return the input flattened to an array.
	
	input: any variable composed of lists/generators/tuples, strings, lambda functions or other 
	objects, nested arbitrarily.
	
	Empty strings and None items are removed. 
	
	Returns a list of strings or other objects depth 1. 

	>>> flatten('hi')
	['hi']
	>>> flatten(['hi', 'ho', 'hum'])
	['hi', 'ho', 'hum']
	>>> flatten(['hi', ['ho', ['hum'] ] ])
	['hi', 'ho', 'hum']
	>>> flatten(['hi', ('ho', ('hum') ) ])
	['hi', 'ho', 'hum']
	>>> flatten(3)
	[3]
	>>> flatten( (x + 1) for x in [1,2,3])
	[2, 3, 4]
	>>> flatten(lambda: '3')
	['3']
	>>> flatten(['hi', lambda: 'ho', 'hum'])
	['hi', 'ho', 'hum']
	>>> flatten(None)
	[]
	"""
	if not input: return []
	if isinstance(input, (list, tuple, set, types.GeneratorType)):
		rv = []
		for l in input:
			rv = rv + flatten(l)
		return rv
	elif hasattr(input, 'resolveToString'): # Composeable, etc - delayed
		return [input]
	elif hasattr(input, '__call__'): # a zero-arg lambda
		return flatten(input())
	else:
		return [input]
		
def getStringList(stringOrListOfStrings) -> list[str]:
	""" Return a list of strings, either identical to the input (if it's already a list), or with the input wrapped in 
	a new sequence (if it's a string), or an empty sequence (if its None). 
	
	>>> getStringList('abc')
	['abc']
	
	>>> getStringList(['abc', 'def'])
	['abc', 'def']

	>>> getStringList(('abc', 'def'))
	['abc', 'def']

	>>> getStringList(tuple(['abc', 'def']))
	['abc', 'def']

	>>> getStringList([['abc', 'def']])
	['abc', 'def']
	
	>>> getStringList(None)
	[]
	
	>>> getStringList(5)
	Traceback (most recent call last):
	...
	ValueError: The specified value must be a list of strings: "5"
	"""
	if stringOrListOfStrings == None:
		return []
	if isinstance(stringOrListOfStrings, tuple):
		stringOrListOfStrings = list(stringOrListOfStrings)

	if isinstance(stringOrListOfStrings, list):
		if len(stringOrListOfStrings)==1 and isinstance(stringOrListOfStrings[0], list):
			return stringOrListOfStrings[0]
		return stringOrListOfStrings
	elif isinstance(stringOrListOfStrings, str):
		return [stringOrListOfStrings]
	raise ValueError('The specified value must be a list of strings: "%s"'%(stringOrListOfStrings))


from xpybuild.utils.functors import Composable

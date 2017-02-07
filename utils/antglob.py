# antglob - algorithm for globbing ant-style path expressions
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
# $Id: antglob.py 301527 2017-02-06 15:31:43Z matj $
#

from buildexceptions import BuildException
import re

def antGlobMatch(pattern, path):
	"""
	Matches a path against an ant-style glob pattern which may contain 
	'*' or '**'. 
	
	If the path is a directory, it must end with a slash. 
	Patterns ending with a '/' can only match directories, and patterns without 
	can only match files. 
	
	>>> antGlobMatch('', '')
	True

	>>> antGlobMatch('*', 'a')
	True

	>>> antGlobMatch('*.b', 'a')
	False

	>>> antGlobMatch('*.b', 'a.b')
	True

	>>> antGlobMatch('b.*', 'b')
	False

	>>> antGlobMatch('b.*', 'b.a')
	True

	>>> antGlobMatch('a*b', 'ab')
	True

	>>> antGlobMatch('a*b', '')
	False

	>>> antGlobMatch('a*b', 'axxxb')
	True

	>>> antGlobMatch('a*b', 'axxx')
	False
	
	>>> antGlobMatch('a*b', 'xxxb')
	False

	>>> antGlobMatch('a/b.*/c', 'a/b.x/c')
	True

	>>> antGlobMatch('a/b.*/c', 'a/b/c')
	False

	>>> antGlobMatch('**', 'a')
	True

	>>> antGlobMatch('**', 'a/b/c')
	True

	>>> antGlobMatch('**/c', 'a/b/c')
	True

	>>> antGlobMatch('**/*c', 'c')
	True

	>>> antGlobMatch('**/b/c', 'a/b/c')
	True

	>>> antGlobMatch('**/d', 'a/b/c')
	False

	>>> antGlobMatch('a/**/b', 'a/b/c')
	False

	>>> antGlobMatch('a/b/**', 'a/b/c/d')
	True

	>>> antGlobMatch('a/b/**/*', 'a/b/c/d')
	True

	>>> antGlobMatch('a/**/b', 'a/b')
	True

	>>> antGlobMatch('a/b/**', 'a/b')
	True

	>>> antGlobMatch('a/b', 'a/b/c/d')
	False

	>>> antGlobMatch('a/**/d/e', 'a/b/c/d/e')
	True

	>>> antGlobMatch('*x/**/', 'x/a/b/')
	True

	>>> antGlobMatch('*x/**', 'x/a/b')
	True

	>>> antGlobMatch('*x/**/', 'x/a/b')
	False

	>>> antGlobMatch('*x/**', 'x/a/b/')
	False

	>>> antGlobMatch('*[[*', '[[') and antGlobMatch('*[[*', 'xx[[') and antGlobMatch('*ab*', 'abxx')
	True

	>>> antGlobMatch('*[]*', '[')
	False

	>>> antGlobMatch('aa*.b*c*/', 'aa.bc/') and antGlobMatch('aa*.b*c*/', 'aaxxx.bxcxx/')
	True

	>>> antGlobMatch('aa*b*c*', 'xaabc')
	False

	>>> antGlobMatch('aa*.*c*', 'aaYc')
	False

	>>> antGlobMatch('**/*.x', 'a/b.x/c.x')
	True

	>>> antGlobMatch('**/*.x', 'a/b.x/c.x/d.x')
	True

	>>> antGlobMatch('**/*.x', 'a/c.x/y/d.x')
	True

	>>> antGlobMatch('**/*.x', 'a/y/c.x/d.x')
	True

	>>> antGlobMatch('**/**/*.x', 'a/y/c.x/d.x')
	True

	>>> antGlobMatch('**/*.x/', 'a/y/c.x/d.x/')
	True

	"""
	# this is an algorithm similar to ant's globbing... but not totally identical (to keep things simple), it doesn't support '?' for example
	# we also distinguish between file and dir patterns
	
	# we avoid using regexes for efficiency reasons
	
	if pattern.endswith('/') != path.endswith('/'):
		return False
	pattern = pattern.rstrip('/')
	path = path.rstrip('/')
	
	if pattern.endswith('**/*'): pattern = pattern[:-2]
	pattern = pattern.split('/')
	path = path.split('/')

	if '?' in pattern: 
		 # would require some more work (maybe regexes), but a rare case so don't bother
		raise BuildException('Invalid pattern ("?" is not supported at present): %s'%pattern)
	
	def elementMatch(elementPattern, element):
		# NB: do this case sensitively, because that's what unix will do anyway
		if elementPattern == '*' or elementPattern == '**':
			return True

		if '**' in elementPattern:
			raise BuildException('Invalid pattern (pattern elements containing "**" must not have any other characters): %s'%pattern)

		elementPattern = elementPattern.split('*')
		
		# simple cases, efficient implementation
		if len(elementPattern) == 1:
			return elementPattern[0] == element
		if len(elementPattern) == 2: # copes with: a* *a and a*b
			return element.startswith(elementPattern[0]) and element.endswith(elementPattern[1])
		
		return re.match('.*'.join(map(re.escape, elementPattern)), element)
	
	x = y = 0
	while x < len(pattern) and y < len(path):
		if pattern[x] == '**':
			if x == len(pattern)-1:
				return True
			else:
				# consume as much as we need to of ** until we get another match
				# (try to be greedy - should ignore matches that are too early, i.e. don't leave 
				# enough remaining elements to possibly match. If the rest of 
				# the pattern contains a ** this might still not do quite the 
				# right thing, perhaps a recursive algorithm is needed to 
				# cope with case)
				x += 1
				while y < len(path) and (not elementMatch(pattern[x], path[y]) or len(pattern)-x < len(path)-y):
					y += 1
		else:
			if not elementMatch(pattern[x], path[y]):
				return False
			x += 1
			y += 1
	
	if x == len(pattern):
		if y == len(path): # got to the end of both
			return True
	
		# pattern didn't end in ** but there's still some unmatched path, so we failed
		return False

	# we've run out of path
	return pattern[x] == '**' # ** may happily match nothing
	

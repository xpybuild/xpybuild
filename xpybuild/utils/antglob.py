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

"""
Ant-style ``**/*`` globbing functionality, as used by `xpybuild.pathsets.FindPaths`. 
"""

from xpybuild.utils.buildexceptions import BuildException
import re, logging, sys
from xpybuild.utils.flatten import flatten

_log = logging.getLogger('antglob')

#def dbg(s, *args): # for manual use with doc tests
#	sys.stderr.write((s%args)+'\n')
#	sys.stderr.flush()

class GlobPatternSet(object):
	"""
	Holds a set of one or more ant-style glob patterns, which can be used to 
	filter a set of paths based on whether each path matches any of the 
	specified patterns. 
	
	Typically there will be one GlobPatternSet for includes and another for 
	excludes. 
	
	This object is immutable and thread-safe.
	
	Glob patterns may contain '*' (indicating zero or more non-slash 
	characters) or '**' (indicating zero or more characters including slashes). 
	The '?' character is not supported. 
	
	"""
	__patternCache = {} # static cache, since there will be lots of these; mostly to save memory, but also a bit of CPU
	__patternCache_get = __patternCache.get
	
	# define these so we can use fast 'is' comparisons
	STAR = '*'
	STARSTAR = '**'
	
	@staticmethod
	def create(patterns):
		"""
		Create a new GlobPatternSet for matching any of the specified patterns. 
		
		Patterns ending with a '/' can only match directories, and patterns without 
		can only match files. 

		@param patterns: a string, or a list of one or more pattern strings. 
		Glob patterns may contain '*' (indicating zero or more non-slash 
		characters) or '**' (indicating zero or more characters including slashes). 
		Backslashes are not permitted. Empty pattern strings are ignored. 

		"""
		if isinstance(patterns, list): patterns = tuple(patterns) # make it hashable
		if patterns in GlobPatternSet.__patternCache: 
			return GlobPatternSet.__patternCache[patterns]
		
		p = GlobPatternSet(patterns)
		GlobPatternSet.__patternCache[patterns] = p
		return p
	
	def __init__(self, patterns):
		""" Do not call the ``GlobPatternSet()`` constructor - use L{create} instead of constructing directly.
		"""
		patterns = flatten(patterns)
		
		# values are [ELEMENTS, ORIGINAL_PATTERNS_INDEX]
		self.filepatterns = []
		self.dirpatterns = [] # with no trailing slash
		self.origpatterns = [] # original file+dir patterns 

		
		self.hasStarStarPrefixPattern = False # set to true if there are any file or dir patterns starting **/		
		# some booleans to save calculations later
		self.allfiles = False # ** i.e. match all files regardless
		self.alldirs = False
		
		for p in patterns:
			if not p: continue

			if '?' in p:
				 # would require some more work (maybe regexes), but a rare case so don't bother
				raise BuildException('Invalid pattern ("?" is not supported at present): %s'%p)
	
			if '\\' in p:
				raise BuildException('Invalid pattern (must use forward slashes not backslashes): %s'%p)
	
			if p.endswith('**/*'): p = p[:-2] # normalize since this is pointless
				
			if '**/*/' in p:
				# we disallow this because it messes up our ability to decide how many path elements the ** should eat; 
				# breaks cases like >>> antGlobMatch('**/*/f/*.e', 'f/PPP/a/b/c/d/e/PPP/f/foo.e') (ought to be True)
				# in theory we could solve that case by counting from the back, but the potential presence of 
				# **s later in the pattern would make that a very inefficient operation. 
				# There isn't really a compelling case for supporting this so disable it to avoid people
				# shooting themselves in the foot
				raise BuildException('Invalid pattern (**/* sequences are not permitted): %s'%p)
			
			self.origpatterns.append(p)
			if p.startswith('**'): self.hasStarStarPrefixPattern = True
			if p[-1] == '/':
				if p == '**/': self.alldirs = True
				elements = [self.__canonicalizePatternElement(e) for e in p[:-1].split('/')]
				self.dirpatterns.append([elements, len(self.origpatterns)-1])
			else:
				if p == '**': self.allfiles = True
				elements = [self.__canonicalizePatternElement(e) for e in p.split('/')]
				self.filepatterns.append([elements, len(self.origpatterns)-1])

			for e in elements:
				if '**' in e and e != '**':
					raise BuildException('Invalid pattern (pattern elements containing "**" must not have any other characters): %s'%p)
					
		if self.allfiles: assert len(self.filepatterns)==1, 'No point specifying additional file patterns after adding **'
		if self.alldirs: assert len(self.dirpatterns)==1, 'No point specifying additional directory patterns after adding **/'
		
		self.nofiles = self.filepatterns == []
		self.nodirs = self.dirpatterns == []

	@staticmethod
	def __canonicalizePatternElement(element):
		# allow faster comparisons with these common strings
		if element == '*': return GlobPatternSet.STAR
		if element == '**': return GlobPatternSet.STARSTAR
		return element
			
	
	def __str__(self): 
		"""
		>>> str(GlobPatternSet.create(['**/a', '*/b/', '**/c']))
		"['**/a', '*/b/', '**/c']"
		"""
		return str(self.origpatterns)
		
	def __repr__(self): 
		"""
		>>> repr(GlobPatternSet.create(['**/a', '*/b/', '**/c']))
		"GlobPatternSet['**/a', '*/b/', '**/c']"
		"""
		return 'GlobPatternSet%s'%self.__str__()


	def getPathMatches(self, rootdir, filenames=None, dirnames=None, unusedPatternsTracker=None):
		"""
		Check these patterns against one or more basenames (dir names and filenames) 
		within a single root directory and return the list which match at least 
		one pattern. 
		
		Using this method is a lot more efficient than checking each file 
		in a directory independently, especially when there are many files. 
		
		@param rootdir: The parent of the file/dir names to be matched. 
			Must use forward slashes not backslashes, and must end with a slash. 
			Can be empty but not None. 
		
		@param filenames: A list of base file names within the rootdir, to be 
			matched. There must be no empty names in the list, but an empty/None list 
			can be specified. 
			No slash characters may be present in the names. 

		@param dirnames: A list of base directory names within the rootdir, to be 
			matched. There must be no empty names in the list, but an empty/None list 
			can be specified. 
			
			No slash characters may be present in the names, except optionally 
			as a suffix. 
		
		@param unusedPatternsTracker: Optionally specify an instance of 
			`GlobUnusedPatternTracker` which will be notified of the patterns that 
			are used, allow an error to be produced for any that are not used. 
		
		@returns: If either filenames or dirnames is None then the result is a 
			single list of basenames. If both filenames and dirnames are lists 
			(even if empty) the result is a tuple (filenames, dirnames). 
			Directory entries will have a trailing slash only if they did in the input 
			dirnames list.
		
		"""
		# this is an algorithm similar to ant's globbing... but not totally identical (to keep things simple), it doesn't support '?' for example
		# we also distinguish between file and dir patterns
		
		# we avoid using regexes for efficiency reasons
		
		operations = []

		if unusedPatternsTracker is None:
			unusedPatternsTrackerIndex = None
		else: # speed up lookups since this is frequent
			unusedPatternsTrackerIndex = unusedPatternsTracker._used

		if filenames is not None:
			fileresults = []
			if filenames != []:
				if self.allfiles: # special-case ** to make it fast
					fileresults = filenames
					if unusedPatternsTracker is not None: unusedPatternsTrackerIndex[self.filepatterns[0][1]] = True
				elif not self.nofiles:
					operations.append((self.filepatterns, filenames, False, fileresults))
			results = fileresults
			
		if dirnames is not None:
			dirresults = []
			if dirnames != []:
				if self.alldirs: # special-case **/ to make it fast
					dirresults = dirnames
					if unusedPatternsTracker is not None: unusedPatternsTrackerIndex[self.dirpatterns[0][1]] = True
				elif not self.nodirs:
					operations.append((self.dirpatterns, dirnames, True, dirresults))
			results = dirresults
		
		if dirnames is not None and filenames is not None: results = (fileresults, dirresults)
		if len(operations) == 0: return results

		# this is _very_ performance critical code. we do less validation than 
		# normal to keep it fast - caller needs to pass in clean inputs
		if rootdir is None: 
			rootdir = ''
		else:
			assert rootdir=='' or rootdir[-1]=='/', 'Root directory must end with a slash: %s'%rootdir
		
		if len(rootdir)>0:
			rootdir = rootdir[:-1].split('/')
		else:
			rootdir = []
		rootdirlen = len(rootdir)
		STAR = GlobPatternSet.STAR 
		STARSTAR = GlobPatternSet.STARSTAR
		
		for (patternlist, basenames, isdir, thisresultlist) in operations:
			#if not basenames: continue
			assert '/' not in basenames[0], 'Slashes are not permitted in the base names passed to this function: %s'%basenames[0] # sanity check for correct usage

			# start by finding out which patterns match against basenames in this directory
			basenamepatterns = [] # patterns to match against basenames
			for (patternelements, origpatternindex) in patternlist:
				finalpattern = GlobPatternSet.__matchSinglePath(patternelements, rootdir, rootdirlen)
				if finalpattern is None: continue
				if finalpattern is STARSTAR: finalpattern = STAR #canonicalize further
				basenamepatterns.append( (finalpattern, origpatternindex) )
				if finalpattern is STAR: break # no point doing any others
			
			if len(basenamepatterns) == 0: continue
			if basenamepatterns[0][0] is STAR:
				#special-case this common case
				thisresultlist.extend(basenames)
				if unusedPatternsTracker is not None: unusedPatternsTrackerIndex[basenamepatterns[0][1]] = True
			else:

				for basename in basenames:
					origbasename = basename
					
					if isdir and (basename[-1] == '/'): basename = basename[:-1] # strip off optional dir suffix
					
					for (basenamepattern, origpatternindex) in basenamepatterns:
						if GlobPatternSet.__elementMatch(basenamepattern, basename): 
							thisresultlist.append(basename)
							if unusedPatternsTracker is not None: unusedPatternsTrackerIndex[origpatternindex] = True
							break

		return results

	@staticmethod	
	def __elementMatch(elementPattern, element):
		# NB: do this case sensitively, because that's what unix will do anyway
		if elementPattern is GlobPatternSet.STAR or elementPattern is GlobPatternSet.STARSTAR:
			return True

		# simple cases, efficient implementation
		star1 = elementPattern.find('*')
		if star1 == -1: return elementPattern==element

		star2 = elementPattern.find('*', star1+1)
		if star2 == -1: # copes with: a* *a and a*b
			return element.startswith(elementPattern[:star1]) and element.endswith(elementPattern[star1+1:])

		# more complex cases will have to be less efficient
		elementPattern = elementPattern.split('*')
		return re.match('.*'.join(map(re.escape, elementPattern)), element)

	@staticmethod	
	def __matchSinglePath(pattern, rootdir, lenrootdir):
		# matches all elements of pattern against rootdir/basename where basename 
		# could be anything. Returns None if no match is possible, or the pattern element 
		# string that basenames must match or .STAR/STARSTAR if any. 
		
		#dbg('matching: %s, %s, %s', pattern, rootdir, lenrootdir)
		
		lenpattern = len(pattern)
		STARSTAR = GlobPatternSet.STARSTAR
		
		# nb: pattern is a list of pattern elements; rootdir is rstripped and split by /
		e = y = 0
		while e < lenpattern-1 and y < lenrootdir:
			patternelement = pattern[e]
			#dbg('loop patternelement: %s, %s, %s, %s', patternelement, e, rootdir[y], y)
			if patternelement is STARSTAR:
				if e == lenpattern-2: # this is just an optimization for a common case **/pattern
					# all that remains is the pattern to match against the basename
					return pattern[lenpattern-1]
				else:
					# consume as much as we need to of ** until we get another match
					# be completely greedy; in theory we could try to ignore matches that are too early, i.e. don't leave 
					# enough remaining elements to possibly match (e.g. antGlobMatch('**/PPP/f/*.e', 'f/PPP/a/b/c/d/e/PPP/f/foo.e') )
					# but in practice that gets too hard to handle in case there are further **s later in the pattern. 
					# don't consume the final pattern element since we'll need that to match the basename
					e += 1
					patternelement = pattern[e]
					#dbg('INNER loop patternelement: %s, %s, %s, %s', patternelement, e, rootdir[y], y)
					while y < lenrootdir and not GlobPatternSet.__elementMatch(patternelement, rootdir[y]):
						y += 1
					#dbg('INNER loop done: %s, %s, %s', patternelement, e, y)
			else:
				#dbg('normal patternelement: %s, %s, %s, %s', patternelement, e, rootdir[y], y)
				if not GlobPatternSet.__elementMatch(patternelement, rootdir[y]):
					return None
				e += 1
				y += 1

		if y == lenrootdir:
			# we've used up all the rootdir
			
			while e < lenpattern-1 and pattern[e] is STARSTAR:
				e += 1
			
			if e == lenpattern-1: 
				return pattern[-1]

			if e == lenpattern-2: 
				if pattern[-1] is STARSTAR: 
					return pattern[-2]
			return None
		
		# we have some rootdir left over, only ok if we have a final **
		if e == lenpattern-1 and pattern[-1] is STARSTAR: 
			return STARSTAR
			
		return None
		
	@staticmethod
	def __dirCouldMatchIncludePattern(includePattern, isdir, d):
		# nb: we already checked it doesn't start with ** before calling this function
		d = d.split('/')
		if isdir:
			p = includePattern
		else:
			p = includePattern[:-1] # strip off trailing filename
			
		if GlobPatternSet.STARSTAR not in includePattern and len(d) > len(p): 
			# don't go into a dir structure that's more deeply nested than the pattern
			#log.debug('   maybe vetoing %s based on counts : %s', d, p)
			return False
		
		i = 0
		while i < len(d) and i < len(p) and p[i]:
			if GlobPatternSet.STAR in p[i]: return True # any kind of wildcard and we give up trying to match
			if d[i] != p[i]: 
				#log.debug('   maybe vetoing %s due to not matching %s', d, includePattern)
				return False
			i += 1
		return True
	
	def removeUnmatchableDirectories(self, rootdir, dirnames):
		"""
		Modifies the specifies list of dirnames, removing any which cannot possibly 
		match this include pattern. This is a useful optimization for os.walk. 
		
		As this function is intended as a quick optimization it may leave in some 
		dirs that could not match, but will definitely not remove any that could. 
		
		@param rootdir: The parent of the file/dir names to be matched. 
			Must use forward slashes not backslashes, and must end with a slash. 
			Can be empty but not None. 
		
		@param dirnames: a list of directory basenames contained in rootdir
		
		@returns: the same dirnames instance passed in (with any modifications made). 
		
		>>> GlobPatternSet.create(['**']).removeUnmatchableDirectories('abc/def/', ['dir1', 'dir2'])
		['dir1', 'dir2']

		>>> GlobPatternSet.create(['**/']).removeUnmatchableDirectories('abc/def/', ['dir1', 'dir2'])
		['dir1', 'dir2']

		>>> GlobPatternSet.create(['**/foo']).removeUnmatchableDirectories('abc/def/', ['dir1', 'dir2'])
		['dir1', 'dir2']

		>>> GlobPatternSet.create(['a/b/c/d/**']).removeUnmatchableDirectories('abc/def/', ['dir1', 'dir2'])
		[]

		>>> GlobPatternSet.create(['abc/def/dir1/d/**']).removeUnmatchableDirectories('abc/def/', ['dir1', 'dir2'])
		['dir1']

		>>> GlobPatternSet.create(['abc/def/dir1/d/**/']).removeUnmatchableDirectories('abc/def/', ['dir1', 'dir2'])
		['dir1']
		
		"""
		
		# quick optimizations where we do nothing - everything could match a global wildcard
		if self.allfiles or self.alldirs or self.hasStarStarPrefixPattern: return dirnames
				
		assert rootdir=='' or rootdir[-1]=='/', 'Root directory must end with a slash: %s'%rootdir

		dirnames[:] = [d for d in dirnames if 
			any(self.__dirCouldMatchIncludePattern(e, False, rootdir+d) for e, _ in self.filepatterns) or
			any(self.__dirCouldMatchIncludePattern(e, True, rootdir+d) for e, _ in self.dirpatterns)
			]

		return dirnames

	def matches(self, path):
		"""
		Returns True if the specified path matches any of the patterns in this set 
		or False if not. 
		
		Note that L{getPathMatches} is considerably more efficient than this method 
		when there are several paths to be matched in the same directory. 
		
		@param path: A path string. Must not be empty, must not contains 
		backslashes, and must end with a slash if it is a directory. 
		"""
		if path[-1]=='/':
			path = path[:-1].split('/')
			return self.getPathMatches('/'.join(path[:-1])+'/' if len(path)>1 else None, dirnames=[path[-1]]) != []
		else:
			path = path.split('/')
			return self.getPathMatches('/'.join(path[:-1])+'/' if len(path)>1 else None, filenames=[path[-1]]) != []

class GlobUnusedPatternTracker(object):
	"""
	Class for recording which patterns have successfully been used in a match, 
	in order to provide error messages or warnings listing unused patterns. 
	
	This object should not be shared between threads.
	"""
	def __init__(self, patternSet):
		self._patterns = patternSet.origpatterns
		self._used = [False for i in range(len(self._patterns))]
	
	def getUnusedPatterns(self):
		"""
		Returns a list of the patterns that have not been used. 
		"""
		unused = []
		for i in range(len(self._patterns)):
			if not self._used[i]: unused.append(self._patterns[i])
		return unused

		
def antGlobMatch(pattern, path):
	"""
	Matches a path against an ant-style glob pattern which may contain 
	``*`` or ``**``. 
	
	If the path is a directory, it must end with a slash. 
	Patterns ending with a ``/`` can only match directories, and patterns without 
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

	>>> antGlobMatch('a/b/c/d/e/**', 'a/b/c')
	False

	>>> antGlobMatch('**/PPP/**/*.e', 'a/b/c/d/e/f/PPP/g/h/i/foo.e')
	True

	>>> antGlobMatch('**/PPP/**/*.e', 'PPP/g/h/i/foo.e')
	True

	>>> antGlobMatch('**/PPP/**/*.e', 'a/b/c/d/e/f/PPP/foo.e')
	True

	>>> antGlobMatch('**/PPP/**/*.e', 'a/b/PPP/g/h/i/j/k/l/m/n/o/foo.e')
	True

	>>> antGlobMatch('**/PPP/**/*.e', 'a/b/c/d/e/f/g/h/i/foo.e')
	False

	>>> antGlobMatch('**/PPP/**/**/**/PPP/**/**/*.e', 'f/PPP/x/PPP/foo.e')
	True

	>>> antGlobMatch('**/PPP/f/*.e', 'f/PPP/a/b/c/d/e/PPP/f/foo.e') # this one is debatable (could decide not to match first PPP to allow second to match, but in general hard to reliably detect that condition given any later **s would invalidate any attempt to do it by counting); this behaviour is simpler to describe and more efficient to implement
	False

	>>> antGlobMatch('*/**/f/*.e', 'f/PPP/a/b/c/d/e/PPP/f/foo.e') 
	True

	"""
	if not path: return not pattern # not useful or ideal, but for compatibility with older users keep this behaviour the same

	return GlobPatternSet.create(pattern).matches(path)
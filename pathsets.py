# xpyBuild - eXtensible Python-based Build System
#
# This module holds definitions for various PathSet classes. A path set is a 
# lazily-resolved, thread-safe set of file/directory absolute paths, with 
# an optional (perhaps trivial) mapping to relative 'destination' paths 
# (which is used by some targets, e.g. copy). Where possible, ordering of 
# the items in a compound pathset is preserved. 
#
# A PathSet's contents are not resolved until after the 
# initialization phase of the build is complete, since resolution may involve 
# expensive file system operations. 
#
# When using a pathset to specify paths located under a directory that 
# is generated as part of the build process, always use 
# DirGeneratedByTarget(dirpath) to wrap the reference to the generated 
# directory, which forces the evaluation of its contents to be delayed 
# until the target dependency has actually been built.
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
# $Id: pathsets.py 301527 2017-02-06 15:31:43Z matj $
#

import os, sys
import threading
import logging
import time
from utils.antglob import antGlobMatch
from utils.flatten import flatten
from utils.buildfilelocation import BuildFileLocation
from utils.fileutils import normLongPath
from buildexceptions import BuildException
from buildcommon import isDirPath, normpath
from buildcontext import BaseContext, getBuildInitializationContext

# don't define a 'log' variable here or targets will use it by mistake when importing this file

class BasePathSet(object):
	""" Base class for PathSet implementations. 

	This is a stub class and should not be used directly.
	"""
	def __init__(self):
		pass
	
	def __repr__(self):
		raise Exception('TODO: must implement __repr__ for %s'%self.__class__)
	
	def resolve(self, context):
		""" Use the specified context to resolve the contents of this pathset 
		to a list of normalized absolute paths (using OS-dependent slashes). 
		
		All directory paths must end with "/" or "\". 
		
		Some PathSet implementations will cache the results of resolve, if 
		expensive (e.g. file system globbing); in such case it is essential to 
		ensure that the implementation is thread-safe. 
		
		PathSets can contain duplicate entries (with same source and/or 
		destination). 
		"""
		return [src for (src,dest) in self.resolveWithDestinations(context)]

	def resolveWithDestinations(self, context):
		""" Use the specified context to resolve the contents of this pathset 
		to a list of (srcabs, destrel) pairs specifying the absolute and 
		normalized path of each source path, 
		and a relative normalized delimited path indicating the destination of that 
		path (interpreted in a target-specific way by certain targets 
		such as copy and zip). 
		
		All paths use OS-dependent slash characters (os.path.sep), 
		and all directory paths must end with a slash to avoid confusion with 
		file paths. 
		
		Some PathSet implementations will cache the results of resolve, if 
		expensive (e.g. file system globbing); in such case it is essential to 
		ensure that the implementation is thread-safe. 

		May raise BuildException if the resolution fails.

		PathSets can contain duplicate entries (with same source and/or 
		destination). 

		"""
		
		raise Exception('TODO: must implement resolveWithDestinations for %s'%self.__class__)
	
	def _resolveUnderlyingDependencies(self, context):
		""" Use the specified context to resolve to a list of the absolute source 
		paths making up this set, for the purposes of target dependency 
		evaluation. The underlying dependency paths are returned, 
		i.e. a child-first delegation model in cases where pathsets are wrapped 
		inside other pathsets, to ensure that where relevant the target 
		responsible for generating derived resources gets returned as the 
		dependency. 
		
		This method is not for use by targets, and should be called just once 
		during the dependency evaluation phase. 
		
		For pathsets that definitely have no PathSet dependencies, this 
		can be implemented as return self.resolve(context)
		"""
		raise Exception('TODO: must implement _resolveUnderlyingDependencies for %s'%self.__class__)


class PathSet(BasePathSet):
	""" A generic/compound PathSet taking as input any combination of strings and 
	other PathSets. 
	"""
	def __init__(self, *inputs):
		"""
		Construct a PathSet from the specified strings and other pathsets. 
		
		@param inputs: contains strings, targets and PathSet objects, nested as deeply as 
		you like within lists and tuples. The strings must be absolute  
		paths or paths relative to the build file where this PathSet is 
		defined, and may not contain the '*' character. Directory 
		paths must end with '/'. 
			
		>>> str(PathSet('a', [('b/', PathSet('1/2/3/', '4/5/6/'), ['d/e'])], 'e/f/${x}').resolveWithDestinations(BaseContext({'x':'X/'}))).replace('\\\\\\\\','/')
		"[('BUILD_DIR/a', 'a'), ('BUILD_DIR/b/', 'b/'), ('BUILD_DIR/1/2/3/', '3/'), ('BUILD_DIR/4/5/6/', '6/'), ('BUILD_DIR/d/e', 'e'), ('BUILD_DIR/e/f/X/', 'X/')]"

		>>> str(PathSet('a', [('b/', PathSet('1/2/3/', '4/5/6/'), ['d/e'])], 'e/f/${x}').resolve(BaseContext({'x':'X/'}))).replace('\\\\\\\\','/')
		"['BUILD_DIR/a', 'BUILD_DIR/b/', 'BUILD_DIR/1/2/3/', 'BUILD_DIR/4/5/6/', 'BUILD_DIR/d/e', 'BUILD_DIR/e/f/X/']"
		
		>>> str(PathSet('a', [('b/', PathSet('1/2/3/', '4/5/6/'), ['d/e'])], 'e/f/${x}'))
		'PathSet("a", "b/", PathSet("1/2/3/", "4/5/6/"), "d/e", "e/f/${x}")'

		>>> str(PathSet('a', [[PathSet('1/2/3/', DirGeneratedByTarget('4/5/6/'), '7/8/')]], DirGeneratedByTarget('9/'))._resolveUnderlyingDependencies(BaseContext({}))).replace('\\\\\\\\','/')
		"['BUILD_DIR/a', 'BUILD_DIR/1/2/3/', 'BUILD_DIR/4/5/6/', 'BUILD_DIR/7/8/', 'BUILD_DIR/9/']"

		>>> PathSet('a/*').resolve(BaseContext({})) #doctest: +IGNORE_EXCEPTION_DETAIL
		Traceback (most recent call last):
		...
		BuildException:
		"""
		super(BasePathSet, self).__init__()
		self.contents = flatten(inputs)
		
		self.__location = None
		for x in self.contents:
			if not (isinstance(x, basestring) or isinstance(x, BasePathSet) or hasattr(x, 'resolveToString')):
				raise BuildException('PathSet may contain only strings, PathSets, Composables, targets and lists - cannot accept %s (%s)'%(x, x.__class__))
		
		self.__location = BuildFileLocation(raiseOnError=True) # may need this to resolve relative paths
		
	def __repr__(self):
		""" Return a string including this class name and the paths from which it was created. """
		return 'PathSet(%s)' % ', '.join(map(lambda s:'"%s"'%s.replace('\\','/') if isinstance(s, basestring) else str(s), self.contents))
	
	def __resolveStringPath(self, p, context): # used for anything that isn't a pathset
		if hasattr(p, 'resolveToString'):
			p = p.resolveToString(context)
		
		p = context.getFullPath(p, self.__location.buildDir, expandList=True)

		for x in p:
			if '*' in x: # sanity check
				raise BuildException('Cannot specify "*" glob patterns here (consider using FindPaths instead): "%s"'%p, location=self.__location)
		# destination is always flat path for things specified absolutely
		# if it's a directory this is a bit inconsistent, but that case doesn't occur so often
		return p, [os.path.basename(x.rstrip('\\/'))+(os.path.sep if isDirPath(x) else '') for x in p]

	def _resolveUnderlyingDependencies(self, context):
		r = []
		for x in self.contents:
			if not isinstance(x, BasePathSet):
				r.extend(self.__resolveStringPath(x, context)[0])
			else:
				# for pathsets, delegate to child
				r.extend(x._resolveUnderlyingDependencies(context))
		
		# check for duplicates here
		seen = set()
		if len(self.contents) > 1: # no point if it's a trivial wrapper around another PathSet
			for x in r:
				if '//' in x: # this could easily confuse things later!
					raise BuildException('Invalid path with multiple slashes "%s" in %s'%(x, self), location=self.__location)
				if x.lower() in seen:
					# originally we had an exception here, but occasionally you might have a single thing that's 
					# a dependency in more than one way (e.g. a jar that's on the classpath AND packaged within an OSGI bundle)
					# so just make this a debug log msg
					logging.getLogger('PathSet').debug('Duplicate PathSet item found: "%s" in %s from %s', x, self, self.__location)
					#raise BuildException('Duplicate item "%s" in %s'%(x, self), location=self.__location)
				seen.add(x.lower())
		
		return r
	
	def resolveWithDestinations(self, context):
		# Docs inherited from base class
		r = []
		for x in self.contents:
			if not isinstance(x, BasePathSet):
				y = self.__resolveStringPath(x, context)
				r.extend(zip(y[0], y[1]))
			else:
				r.extend(x.resolveWithDestinations(context))
		return r
		
def _resolveDirPath(dir, context, location):
	"""
	Helper method for use within this module: 
	resolves a single directory path that may be either a string or a DirGeneratedByTarget. 
	
	This path is guaranteed to be expanded and to end with a trailing / character. 
	"""
	if isinstance(dir, BasePathSet):
		dir = dir.resolve(context)
		if len(dir) != 1: raise BuildException('This PathSet requires exactly one base directory but %d were provided: %s'%(len(dir), dir), location=location) 
		dir = dir[0]
	else:
		dir = context.getFullPath(dir, location.buildDir)
	if not isDirPath(dir):
		raise BuildException('Directory paths must end with an explicit / slash: "%s"'%dir, location=location)
	return dir

class DirBasedPathSet(BasePathSet):
	""" Constructs a pathset using a basedir and a list of (statically defined, 
	non-globbed) basedir-relative paths within it. 
	
	e.g. DirBasedPathSet('${MY_DIR}/', 'a', 'b/', '${MY_JARS[]}', 'x, y, ${Z[]}')

	>>> str(DirBasedPathSet('${MY_DIR}', 'a', 'b/c/', '${MY_JARS[]}', 'd').resolveWithDestinations(BaseContext({'MY_DIR':'MY_DIR/', 'MY_JARS[]':'  1 , 2/3, 4/5/'}))).replace('\\\\\\\\','/')
	"[('BUILD_DIR/MY_DIR/a', 'a'), ('BUILD_DIR/MY_DIR/b/c/', 'b/c/'), ('BUILD_DIR/MY_DIR/1', '1'), ('BUILD_DIR/MY_DIR/2/3', '2/3'), ('BUILD_DIR/MY_DIR/4/5/', '4/5/'), ('BUILD_DIR/MY_DIR/d', 'd')]"

	>>> DirBasedPathSet('mydir', 'a*b').resolve(BaseContext({})) #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
	...
	BuildException:

	>>> str(PathSet('a', DirBasedPathSet(DirGeneratedByTarget('4/5/6/'), '7/8')))
	'PathSet("a", DirBasedPathSet(DirGeneratedByTarget("4/5/6/"), [\\'7/8\\']))'
	
	>>> str(PathSet('a', DirBasedPathSet(DirGeneratedByTarget('4/5/6/'), '7/8'))._resolveUnderlyingDependencies(BaseContext({}))).replace('\\\\\\\\','/')
	"['BUILD_DIR/a', 'BUILD_DIR/4/5/6/']"
	
	"""
	def __init__(self, dir, *children):
		"""
		@param dir: the base directory, which may include substitution variables.
		When fully expanded, it is essential that dir ends with a '/'. 
		May be a string or a DirGeneratedByTarget.

		@param children: strings defining the child files or dirs, which may 
		include ${...} variables but not '*' expansions. Can be specified 
		nested inside tuples or lists if desired. If any of the child 
		strings contains a ${...[]} variable, it will be expanded 
		early and split around the ',' character. 
		"""
		self.__dir = dir
		
		self.__children = flatten(children)
		self.__location = BuildFileLocation(raiseOnError=True)
	
	def __repr__(self):
		""" Return a string including this class name and the basedir and child paths from which it was created. """
		return 'DirBasedPathSet(%s, %s)' % (self.__dir, self.__children)

	def _resolveUnderlyingDependencies(self, context):
		if isinstance(self.__dir, BaseTarget):
			return [self.__dir.resolveToString(context)] 
		elif isinstance(self.__dir, BasePathSet):
			return self.__dir._resolveUnderlyingDependencies(context)
		else:
			return self.resolve(context)
	
	def resolveWithDestinations(self, context):
		children = flatten([
			map(lambda s: s.strip(), context.expandPropertyValues(c, expandList=True))
			for c in self.__children])

		dir = _resolveDirPath(self.__dir, context, self.__location)
		
		result = []
		for c in children:

			if '*' in c: 
				raise BuildException('Cannot specify "*" patterns here (consider using FindPaths instead): "%s"'%c, location=self.__location)
			if os.path.isabs(c):
				raise BuildException('Cannot specify absolute paths here, must be relative (consider using basename): "%s"'%c, location=self.__location)

			isdir = isDirPath(c)

			c=os.path.join(context.expandPropertyValues(dir), c)
			c=os.path.normpath(c.rstrip('\\/'+os.path.sep))

			if isdir: c = c+os.path.sep

			result.append( ( c, c[len(dir):] ) )
		return result
		

class FindPaths(BasePathSet):
	""" A lazily-evaluated PathSet that using * and ** (ant-style) globbing 
	to discover files (and optionally directories) under a common path. 
	
	Is always case-sensitive, will give an error if the dir does not exist 
	or any of the includes fail to match anything. Sorts its output to ensure 
	determinism. 
	
	Includes/excludes are specified using * and ** wildcards (similar to ant), 
	where * represents any path element and ** represents zero or more path 
	elements. Path elements may not begin with a slash, or contain any 
	backslash characters. They match paths underneath the base dir.
	
	Each include/exclude applies either to files OR directories, depending on 
	whether it ends with a '/'. File include/excludes (e.g. 'foo/**') are the 
	most common (and the file '**' pattern is the default include if none is 
	specified). But if used for a target such as a Copy, note that empty 
	directories will NOT be returned by file patterns, so if you wish to 
	copy all empty directories as well as all files, use 
	FindPaths(..., includes=['**', '**/']). 

	Destination paths (where needed) are generated from the path underneath the
	base dir.
	
	@param dir: May be a simple string, or a DirGeneratedByTarget to glob under a 
	directory generated as part of the build. 

	>>> str(FindPaths('a/b/c', includes=['*.x', 'y/**/z/foo.*'], excludes=['xx', '**/y']))
	'FindPaths("a/b/c", includes=["*.x", "y/**/z/foo.*"], excludes=["xx", "**/y"])'

	>>> str(PathSet('a', FindPaths(DirGeneratedByTarget('4/5/6/'), includes='*.xml')))
	'PathSet("a", FindPaths(DirGeneratedByTarget("4/5/6/"), includes=["*.xml"], excludes=[]))'
	
	>>> FindPaths('x', includes=['*.x', 'c:\\d'], excludes=[])#doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
	...
	BuildException:

	>>> FindPaths('x', includes=['*.x', '${foo}'], excludes=[])#doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
	...
	BuildException:

	"""
	def __init__(self, dir, excludes=None, includes=None):
		"""
		@param dir: base directory to search (relative or absolute, may contain ${...} variables). 
		May be a simple string, or a DirGeneratedByTarget to glob under a 
		directory generated as part of the build. 

		@param includes: a list of glob patterns for the files to include (excluding all others)

		@param excludes: a list of glob patterns to exclude after processing any includes.
		"""
		self.__dir = dir
		self.includes = flatten(includes)
		self.excludes = flatten(excludes)
		
		bad = [x for x in (self.includes+self.excludes) if ('//' in x or x.startswith('/') or x.startswith('/') or '\\' in x or '${' in x) ]
		if bad:
			raise BuildException('Invalid includes/excludes pattern in FindPaths - must not contain \\, begin or end with /, or contain substitution variables: "%s"'%bad[0])
		if isinstance(dir, basestring) and '\\' in dir: # avoid silly mistakes, and enforce consistency
			raise BuildException('Invalid base directory for FindPaths - must not contain \\ (always use forward slashes)')
		
		self.location = BuildFileLocation(raiseOnError=True)
		self.__lock = threading.Lock()
		self.__cached = None
	
	def __repr__(self): 
		""" Return a string including this class name and the basedir and include/exclude patterns with which it was created. """
		return ('FindPaths(%s, includes=%s, excludes=%s)'%('"%s"'%self.__dir if isinstance(self.__dir, basestring) else str(self.__dir), self.includes, self.excludes)).replace('\'','"')
	
	def _resolveUnderlyingDependencies(self, context):
		if isinstance(self.__dir, BaseTarget):
			return [self.__dir.resolveToString(context)] 
		elif isinstance(self.__dir, BasePathSet):
			return self.__dir._resolveUnderlyingDependencies(context)
		else:
			return self.resolve(context)
		
	def resolveWithDestinations(self, context):
		"""
		Uses the file system to returns a list of relative paths for files 
		matching the specified include/exclude patterns, throwing a 
		BuildException if none can be found. 

		This method will cache its result after being called the first time. 
		
		"""
		log = logging.getLogger('FindPaths')
		log.debug('FindPaths resolve starting for: %s', self)
		with self.__lock:
			# think this operation is atomically thread-safe due to global interpreter lock
			if self.__cached: return self.__cached
			
			# resolve dir if needed, relative to where the fileset was specified in the build file
			
			resolveddir = _resolveDirPath(self.__dir, context, self.location)

			def dirCouldMatchIncludePattern(includePattern, d):
				if d.startswith('**'): return True
				d = d.split('/')
				p = includePattern.split('/')[:-1] # strip off trailing '' or filename
				if '**' not in includePattern and len(d) > len(p): 
					# don't go into a dir structure that's more deeply nested than the pattern
					#log.debug('   maybe vetoing %s based on counts : %s', d, p)
					return False
				
				i = 0
				while i < len(d) and i < len(p) and p[i]:
					if '*' in p[i]: return True # any kind of wildcard and we give up trying to match
					if d[i] != p[i]: 
						#log.debug('   maybe vetoing %s due to not matching %s', d, includePattern)
						return False
					i += 1
				return True

			matches = []
			try:
				if not os.path.isdir(resolveddir):
					raise BuildException('FindPaths root directory does not exist: "%s"'%os.path.normpath(resolveddir), location=self.location)
				startt = time.time()
				usedIncludes = set() # give an error if any are not used
				longdir = normLongPath(resolveddir)
				visited = 0
				for root, dirs, files in os.walk(longdir):
					visited += 1 
					root = root.replace(longdir, '').replace('\\','/').lstrip('/')
					#log.debug('visiting: "%s"'%root)
					
					# optimization: if this doesn't require walking down the dir tree, don't do any!
					# (this optimization applies to includes like prefix/** but not if there is a bare '**' 
					# in the includes lsit)
					if self.includes and "**" not in self.includes:
						dirs[:] = [d for d in dirs if any(dirCouldMatchIncludePattern(e, (root+'/'+d).lstrip('/')) for e in self.includes)]
					
					# optimization: if there's an exclude starting with this dir and ending with '/**' or '/*', don't navigate to it
					dirs[:] = [d for d in dirs if not 
						next( (e for e in self.excludes if antGlobMatch(e, root+'/'+d)), None)]
					for p in files+[d+'/' for d in dirs]:
						if root: p = root+'/'+p
							
						# first check if it matches an exclude
						if next( (True for e in self.excludes if antGlobMatch(e, p)), False): continue
							
						if not self.includes: # include all files (not directories - that wouldn't make sense or be helpful)
							if not p.endswith('/'):
								matches.append(p)
						else:
							m = next( (i for i in self.includes if antGlobMatch(i, p)), None)
							if m: 
								log.debug('FindPaths matched %s from pattern %s', p, m)
								usedIncludes.add(m)
								matches.append(p)

				log.info('FindPaths in "%s" found %d path(s) for %s after visiting %s directories; %s', resolveddir, len(matches), self, visited, self.location)
				if time.time()-startt > 5: # this should usually be pretty quick, so may indicate a real build file mistake
					log.warn('FindPaths took a long time: %0.1f s to evaluate %s; see %s', time.time()-startt, self, self.location)
				
				if not matches:
					raise BuildException('No matching files found', location=self.location)
				if len(usedIncludes) < len(self.includes): # this is a check that ant doesn't do, but it's helpful for ensuring correctness
					raise BuildException('Some include patterns did not match any files: %s'%', '.join(set(self.includes)-usedIncludes), location=self.location)
						
			except BuildException, e:
				raise BuildException('%s for %s'%(e.toSingleLineString(target=None), self), causedBy=False, location=self.location)
			except Exception, e:
				raise BuildException('%s for %s'%(repr(e), self), causedBy=True, location=self.location)
			
			result = []
			for m in matches:
				result.append( (normpath(resolveddir+'/'+m), normpath(m) ) )
			result.sort()
			
			self.__cached = result
			return result


class TargetsWithTag(BasePathSet):
	"""
	A special PathSet that resolves to all build target output paths marked with the specified tag. 
	
	Note that this is intended mostly for files; it can be used for directories, 
	but only to return the target directory name itself (there is no implicit 
	FindPaths directory searching, as would be required to copy the contents 
	of the directory).
	"""
	def __init__(self, targetTag, allowDirectories=False, walkDirectories=False):
		"""
		@param targetTag: the tag name
		
		@param allowDirectories: set this to True to allow directories to be specified 
		(by default this is False to avoid errors where a directory is 
		used in a Copy without FindPaths, and therefore ends up empty)
		
		@param walkDirectories: implies allowDirectories. Recursively enumerate the 
		contents of the directory at build time.
		"""
		self.__targetTag = targetTag
		self.__location = BuildFileLocation(raiseOnError=True)
		self.__allowDirectories = allowDirectories or walkDirectories
		self.__walkDirectories = walkDirectories
	
	def __repr__(self):
		""" Return a string including this class name and the tag it's looking up. """
		return 'TargetsWithTag(%s, allowDirectories=%s)' % (self.__targetTag, self.__allowDirectories)
	
	def resolveWithDestinations(self, context):
		log = logging.getLogger('TargetsWithTag')
		try:
			targets = context.getTargetsWithTag(self.__targetTag)
		except BuildException, e: # add location info to exception
			raise BuildException(str(e), location=self.__location)
		
		log.info('%s matched %s targets: %s', self, len(targets), [t.name for t in targets])
		if not self.__allowDirectories:
			if [t for t in targets if isDirPath(t.path)]:
				raise BuildException('Invalid attempt to use TargetsWithTag with a tag that includes some directories (set allowDirectories=True if this is really intended): %s'%self, location=self.__location)

		results = []
		for t in targets:
			if self.__walkDirectories and isDirPath(t.path) and os.path.exists(t.path):
				# walk the directory
				for root, dirs, files in os.walk(t.path):
					results.append((root+('' if isDirPath(root) else '/'), os.path.basename(root)+'/')) # add each directory
					for f in files:
						results.append(( normpath(root+('' if isDirPath(root) else '/')+f), f)) # add each file
			else:
				results.append((t.path, os.path.basename(t.path)+('/' if isDirPath(t.path) else '')))
		return results
	
	def _resolveUnderlyingDependencies(self, context):
		log = logging.getLogger('TargetsWithTag')
		try:
			targets = context.getTargetsWithTag(self.__targetTag)
		except BuildException, e: # add location info to exception
			raise BuildException(str(e), location=self.__location)
		return [t.path for t in targets]

	
# PathSets derived from other PathSets:

class _DerivedPathSet(BasePathSet):
	def __init__(self, pathSet):
		self._pathSet = pathSet
		assert isinstance(pathSet, BasePathSet)
	def _resolveUnderlyingDependencies(self, context):
		return self._pathSet._resolveUnderlyingDependencies(context)

class FilteredPathSet(_DerivedPathSet):
	""" Filters the contents of another PathSet using a lambda includeDecider 
	function. 
	
	>>> str(FilteredPathSet(isDirPath, PathSet('a', 'b/', 'd/e', 'e/f/', 'g${x}')).resolveWithDestinations(BaseContext({'x':'/x/'}))).replace('\\\\\\\\','/')
	"[('BUILD_DIR/b/', 'b/'), ('BUILD_DIR/e/f/', 'f/'), ('BUILD_DIR/g/x/', 'x/')]"

	>>> str(FilteredPathSet(isDirPath, PathSet('a', 'b/', 'd/e', 'e/f/', 'g${x}')))
	'FilteredPathSet(isDirPath, PathSet("a", "b/", "d/e", "e/f/", "g${x}"))'
	
	>>> str(PathSet('a', FilteredPathSet(lambda x: True, DirGeneratedByTarget('4/5/6/'))))
	'PathSet("a", FilteredPathSet(<lambda>, DirGeneratedByTarget("4/5/6/")))'
	
	>>> str(PathSet('a', FilteredPathSet(isDirPath, DirGeneratedByTarget('4/5/6/')))._resolveUnderlyingDependencies(BaseContext({}))).replace('\\\\\\\\','/')
	"['BUILD_DIR/a', 'BUILD_DIR/4/5/6/']"

	>>> str(PathSet('a', FilteredPathSet(lambda p:p.endswith('.java'), FindPaths(DirGeneratedByTarget('4/5/6/'))))._resolveUnderlyingDependencies(BaseContext({}))).replace('\\\\\\\\','/')
	"['BUILD_DIR/a', 'BUILD_DIR/4/5/6/']"

	
	"""
	def __init__(self, includeDecider, pathSet, delayFiltration=False):
		"""
		Construct a PathSet that filters its input, e.g. allows only 
		directories or only files. 
		
		@param includeDecider: a function that takes an absolute resolved path and 
		returns True if it should be included
		
		@param delayFiltration: don't filter for dependencies, only for the set used
		at build time
		"""
		_DerivedPathSet.__init__(self, pathSet)
		self.__includeDecider = includeDecider
		self.__delayFiltration = delayFiltration
	
	def __repr__(self):
		""" Return a string including this class name, the functor and the included PathSet. """
		return 'FilteredPathSet(%s, %s)' % (self.__includeDecider.__name__, self._pathSet)
	
	def resolveWithDestinations(self, context):
		result = self._pathSet.resolveWithDestinations(context)
		return [(src, dest) for (src, dest) in result if self.__includeDecider(src)]

	def _resolveUnderlyingDependencies(self, context):
		# run the filter on all files, since that's always safe (and 
		# may significantly improve performance), but don't 
		# filter out any directories at this stage since they might be 
		# DirGeneratedByTarget and we might filter out a directory containing 
		# matching files prematurely
		result = self._pathSet._resolveUnderlyingDependencies(context)
		return result if self.__delayFiltration else [src for src in result if isDirPath(src) or self.__includeDecider(src)]

class AddDestPrefix(_DerivedPathSet):
	""" Adds a specified prefix on to the destinations of the specified PathSet. 
	(the PathSet's source paths are unaffected)
	
	See also RemoveDestParents which does the inverse. 

	e.g. AddDestPrefix('META-INF/', mypathset)
	
	>>> str(AddDestPrefix('lib/bar/', DirBasedPathSet('mydir/', 'b/', 'd/e', 'e/f/')).resolveWithDestinations(BaseContext({}) )).replace('\\\\\\\\','/')
	"[('BUILD_DIR/mydir/b/', 'lib/bar/b/'), ('BUILD_DIR/mydir/d/e', 'lib/bar/d/e'), ('BUILD_DIR/mydir/e/f/', 'lib/bar/e/f/')]"

	>>> str(AddDestPrefix('lib', DirBasedPathSet('mydir/', 'b/', 'd/e', 'e/f/')).resolveWithDestinations(BaseContext({}) )).replace('\\\\\\\\','/')
	"[('BUILD_DIR/mydir/b/', 'libb/'), ('BUILD_DIR/mydir/d/e', 'libd/e'), ('BUILD_DIR/mydir/e/f/', 'libe/f/')]"

	>>> str(AddDestPrefix('/lib', DirBasedPathSet('mydir/', 'b/', 'd/e', 'e/f/')).resolveWithDestinations(BaseContext({}) )).replace('\\\\\\\\','/')
	"[('BUILD_DIR/mydir/b/', 'libb/'), ('BUILD_DIR/mydir/d/e', 'libd/e'), ('BUILD_DIR/mydir/e/f/', 'libe/f/')]"

	>>> str(AddDestPrefix('lib/bar/', PathSet('a', 'b/', 'd/e', 'e/f/')))
	'AddDestPrefix(prefix="lib/bar/", PathSet("a", "b/", "d/e", "e/f/"))'

	"""
	def __init__(self, prefix, pathSet):
		""" Construct an AddDestPrefix from a PathSet, path or list of paths/path sets.

		@param prefix: a string that should be added to the beginning of each dest 
		path. Usually this will end with a slash '/'. 

		@param pathSet: either a PathSet object of some type or something from which a
		path set can be constructed.
		"""
		if not isinstance(pathSet, BasePathSet): pathSet = PathSet(pathSet)
		_DerivedPathSet.__init__(self, pathSet)
		self.__prefix = prefix.lstrip('\\/')
		if '..' in self.__prefix:
			raise BuildException('Cannot use ".." in a dest prefix: %s'%self)
	
	def __repr__(self):
		""" Return a string including this class name, the prefix to add and the pathset 
		from which it was created.
		"""
		return 'AddDestPrefix(prefix="%s", %s)' % (self.__prefix, self._pathSet)
	
	def resolveWithDestinations(self, context):
		# Documentation from base class
		result = self._pathSet.resolveWithDestinations(context)
		prefix = context.expandPropertyValues(self.__prefix).lstrip('\\/')
		return [(key, os.path.normpath(prefix+value)+(os.path.sep if isDirPath(key) else '')) for (key,value) in result]

class MapDest(_DerivedPathSet):
	""" Applies a functor to the destination paths of the enclosed PathSet
	(the PathSet's source paths are unaffected)
	
	Note that paths passed to the functor will always have forward slashes. 

	e.g. MapDest(lambda x:x.lower(), mypathset)
	
	>>> str(MapDest(lambda x: x.rstrip('/')+'_foo', PathSet('a', 'b/', 'c${c}')).resolveWithDestinations(BaseContext({'c':'C/'}))).replace('\\\\\\\\','/')
	"[('BUILD_DIR/a', 'a_foo'), ('BUILD_DIR/b/', 'b_foo/'), ('BUILD_DIR/cC/', 'cC_foo/')]"
	
	>>> str(MapDest(lambda x: x+'_foo', PathSet('a', 'b/', 'c${c}')))
	'MapDest(<lambda>, PathSet("a", "b/", "c${c}"))'

	"""
	def __init__(self, fn, pathSet):
		"""
		@param fn: a function that takes a resolved dest path (using forward slashes 
		not backslashes) as input, and returns a potentially different dest path
		"""
		if not isinstance(pathSet, BasePathSet): pathSet = PathSet(pathSet)
		_DerivedPathSet.__init__(self, pathSet)
		self.__fn = fn
	
	def __repr__(self):
		return 'MapDest(%s, %s)' % (self.__fn.__name__, self._pathSet)
	
	def resolveWithDestinations(self, context):
		result = self._pathSet.resolveWithDestinations(context)
		return [(key, os.path.normpath(context.expandPropertyValues(self.__fn(value.replace('\\','/'))))+(os.path.sep if isDirPath(key) else '')) for (key,value) in result]

class MapSrc(_DerivedPathSet):
	""" Applies a functor to the src paths of the enclosed PathSet to get new destinations
	(the PathSet's source paths are unaffected)
	
	Note that paths passed to the functor will always have forward slashes. 

	e.g. MapSrc(lambda x:x.lower(), mypathset)
	
	"""
	def __init__(self, fn, pathSet):
		"""
		@param fn: a function that takes a resolved dest path (using forward slashes 
		not backslashes) as input, and returns a potentially different dest path
		"""
		if not isinstance(pathSet, BasePathSet): pathSet = PathSet(pathSet)
		_DerivedPathSet.__init__(self, pathSet)
		self.__fn = fn
	
	def __repr__(self):
		return 'MapSrc(%s, %s)' % (self.__fn.__name__, self._pathSet)
	
	def resolveWithDestinations(self, context):
		result = self._pathSet.resolveWithDestinations(context)
		return [(key, os.path.normpath(context.expandPropertyValues(self.__fn(key.replace('\\','/'))))+(os.path.sep if isDirPath(key) else '')) for (key,value) in result]

class FlattenDest(_DerivedPathSet):
	""" Removes all prefixes from the destinations of the specified PathSet. 
	
	e.g. FlattenDest(mypathset)
	
	>>> str(FlattenDest(PathSet('a', 'b/', 'd/e', 'e/f/')))
	'FlattenDest(PathSet("a", "b/", "d/e", "e/f/"))'
	
	"""
	def __init__(self, pathSet):
		"""
		@param pathSet: The input PathSet, path or list of path/PathSets.
		"""
		_DerivedPathSet.__init__(self, pathSet)
	
	def __repr__(self):
		""" Return a string including this class name and the included PathSet. """
		return 'FlattenDest(%s)' % (self._pathSet)
	
	def resolveWithDestinations(self, context):
		result = self._pathSet.resolveWithDestinations(context)
		return [(key, os.path.basename(value.rstrip('\\/'))+(os.path.sep if isDirPath(key) else '')) for (key,value) in result]

class RemoveDestParents(_DerivedPathSet):
	""" Strips one or more parent directory elements from the start of 
	the destinations of the specified PathSet. 
	(the PathSet's source paths are unaffected)
	
	e.g. RemoveDestParents(2, mypathset) # strips the leading 2 parent dirs
	
	See also AddDestPrefix which does the inverse. 

	>>> str(RemoveDestParents(1, DirBasedPathSet('mydir/', ['d/e', 'e/f/g/'])).resolveWithDestinations(BaseContext({}) )).replace('\\\\\\\\','/')
	"[('BUILD_DIR/mydir/d/e', 'e'), ('BUILD_DIR/mydir/e/f/g/', 'f/g/')]"

	>>> str(RemoveDestParents(2, DirBasedPathSet('mydir/', ['a/b/c', 'a/b/c/d', 'd/e/f/', 'd/e/f/g/'])).resolveWithDestinations(BaseContext({}) )).replace('\\\\\\\\','/')
	"[('BUILD_DIR/mydir/a/b/c', 'c'), ('BUILD_DIR/mydir/a/b/c/d', 'c/d'), ('BUILD_DIR/mydir/d/e/f/', 'f/'), ('BUILD_DIR/mydir/d/e/f/g/', 'f/g/')]"

	>>> str(RemoveDestParents(1, DirBasedPathSet('mydir/', 'a')).resolveWithDestinations(BaseContext({}) )).replace('\\\\\\\\','/') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
	...
	BuildException: Cannot strip 1 parent dir(s) from "a" as it does not have that many parent directories

	>>> str(RemoveDestParents(1, DirBasedPathSet('mydir/', 'b/')).resolveWithDestinations(BaseContext({}) )).replace('\\\\\\\\','/')
	Traceback (most recent call last):
	...
	BuildException: Cannot strip 1 parent dir(s) from "b/" as it does not have that many parent directories

	"""
	def __init__(self, dirsToRemove, pathSet):
		""" Construct an RemoveDestParents from a PathSet, path or list of paths/path sets.

		@param dirsToRemove: the number of parent directory elements to remove

		@param pathSet: either a PathSet object of some type or something from which a
		path set can be constructed.
		"""
		assert dirsToRemove > 0
		if not isinstance(pathSet, BasePathSet): pathSet = PathSet(pathSet)
		_DerivedPathSet.__init__(self, pathSet)
		self.__dirsToRemove = dirsToRemove
	
	def __repr__(self):
		""" Return a string including this class name, the prefix to add and the pathset 
		from which it was created.
		"""
		return 'RemoveDestParents(%d, %s)' % (self.__dirsToRemove, self._pathSet)
	
	def resolveWithDestinations(self, context):
		# Documentation from base class
		result = self._pathSet.resolveWithDestinations(context)
		def processDest(p):
			if not p: return p
			p = p.replace('\\','/').split('/')
			# p[-1]=='' if p itself is a directory
			if len(p) - (0 if p[-1] else 1) > self.__dirsToRemove:
				return normpath('/'.join(p[self.__dirsToRemove:]))
			else:
				raise BuildException('Cannot strip %d parent dir(s) from "%s" as it does not have that many parent directories'%(self.__dirsToRemove, '/'.join(p)))
		
		return [(key, processDest(value)) for (key,value) in result]

class SingletonDestRenameMapper(_DerivedPathSet):
	""" Uses the specified hardcoded destination name for the specific file 
	(and checks only a single input is supplied). 
	Properties in the specified dest prefix string will be expanded
	
	e.g. (SingletonDestRenameMapper('meta-inf/manifest.mf', 'foo/mymanifest').
	
	>>> str(SingletonDestRenameMapper('meta-inf/manifest.mf', 'foo/bar'))
	'SingletonDestRenameMapper(meta-inf/manifest.mf, PathSet("foo/bar"))'
	
	>>> str(SingletonDestRenameMapper('meta-inf/manifest.mf', 'foo/mymanifest').resolveWithDestinations(BaseContext({}))).replace('\\\\\\\\','/')
	"[('BUILD_DIR/foo/mymanifest', 'meta-inf/manifest.mf')]"
	
	"""
	def __init__(self, newDestRelPath, pathSet):
		"""
		@param newDestRelPath: Replacement destination path (including file name)

		@param pathSet: The input path or PathSet, which must contain a single file.
		"""
		if not isinstance(pathSet, BasePathSet): pathSet = PathSet(pathSet)
		_DerivedPathSet.__init__(self, pathSet)
		self.newDestRelPath = newDestRelPath
		if isinstance(self.newDestRelPath, basestring): assert '\\' not in self.newDestRelPath
	
	def __repr__(self):
		""" Return a string including this class name, the new destination and the included PathSet. """
		return 'SingletonDestRenameMapper(%s, %s)' % (self.newDestRelPath, self._pathSet)
	
	def resolveWithDestinations(self, context):
		result = self._pathSet.resolveWithDestinations(context)
		if len(result) != 1: raise Exception('This pathset can only be used with a single path: %s', self)
		return [(result[0][0], context.expandPropertyValues(self.newDestRelPath))]

class DirGeneratedByTarget(BasePathSet):
	""" This special PathSet must be used for the base dir when specifying a PathSet 
	for any paths located under a directory that is generated as part of the build process. 
	
	This forces the evaluation of any parent PathSet to be delayed 
	until the target dependency has actually been built.

	Often used as the first argument of a DirBasedPathSet or FindPaths. 

	As a convenience, the "+" operator can be used to add a string representing 
	a relative path to a DirGeneratedByTarget (which will be converted to the 
	equivalent DirBasedPathSet expression). 

	>>> str(DirGeneratedByTarget('4/5/6/'))
	'DirGeneratedByTarget("4/5/6/")'

	>>> str(DirGeneratedByTarget('4/5/6/')+'foo/${MY_VAR}/bar')
	'DirBasedPathSet(DirGeneratedByTarget("4/5/6/"), [\\'foo/${MY_VAR}/bar\\'])'
	
	"""
	def __init__(self, dirTargetName):
		"""
		@param dirTargetName: The directory that another target will generate.
		"""
		BasePathSet.__init__(self)
		assert isinstance(dirTargetName, basestring)
		assert dirTargetName.endswith('/')
		self.__target = dirTargetName
		self.__location = BuildFileLocation(raiseOnError=True)
		
		if '\\' in dirTargetName: # avoid silly mistakes, and enforce consistency
			raise BuildException('Invalid directory target - must not contain \\ (always use forward slashes)')

	def __repr__(self):
		""" Return a string including this class name and the directory. """
		return 'DirGeneratedByTarget("%s")'%(self.__target)

	def _resolveUnderlyingDependencies(self, context):
		
		# sanity check to avoid user error (but not in doctest mode)
		if hasattr(context, '_isValidTarget') and not context._isValidTarget(self.__target):
			raise BuildException('Unknown target name specified for DirGeneratedByTarget: "%s"'%self.__target, location=self.__location)
		
		# don't need to do anything complicated here, 
		# the magic is that all parent pathsets this is wrapped inside 
		# will always delegate down to this path
		return self.resolve(context)

	def resolveWithDestinations(self, context):
		t = context.getFullPath(self.__target, self.__location.buildDir)
		return [(t, os.path.basename(t.strip('/\\'))+(os.path.sep if isDirPath(t) else '') )]

	def __add__(self, suffix):
		# suffix is probably a string but might be a Composable/callable
		return DirBasedPathSet(self, suffix)

from basetarget import BaseTarget

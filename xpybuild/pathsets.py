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
# $Id: pathsets.py 301527 2017-02-06 15:31:43Z matj $
#

import os, sys
import threading
import logging
import time

from xpybuild.utils.antglob import *
from xpybuild.utils.flatten import flatten
from xpybuild.utils.buildfilelocation import BuildFileLocation
from xpybuild.utils.fileutils import normLongPath
from xpybuild.utils.buildexceptions import BuildException
from xpybuild.buildcommon import isDirPath, normpath, IS_WINDOWS
from xpybuild.buildcontext import BaseContext, getBuildInitializationContext

# don't define a 'log' variable here or targets will use it by mistake when importing this file

class BasePathSet(object):
	""" Base class for PathSet implementations. 

	This is a stub class and should not be used directly.
	"""
	
	_skipDependenciesExistenceCheck = False
	"""
	Special flag that can be set by implementors of a PathSet to indicate that 
	all files returned from _resolveUnderlyingDependencies are known to 
	exist, allowing the scheduler to skip the usual step of checking they are 
	present before the main build begins. Only set this when sure that this 
	is the case. 
	"""

	_shortcutUptodateCheck = False
	"""
	Special flag that can be set by implementors of a PathSet to indicate that 
	the scheduler can take a shorcut and use pathset._newestFile=(path, timestamp) 
	to get the newest file rather than manually calling stat on the dependencies. 
	"""
	
	def __init__(self):
		pass
	
	def __repr__(self):
		raise Exception('TODO: must implement __repr__ for %s'%self.__class__)
	
	def resolve(self, context):
		""" Use the specified context to resolve the contents of this pathset 
		to a list of normalized absolute paths (using OS-dependent slashes). 
		
		Note that unless you actually need a list it is usually more efficient 
		to iterate over resolveWithDestinations which avoids taking a copy of 
		the data structure. 
		
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
		""" Returns a generator or list that uses the specified context to 
		resolve the absolute source paths making up this set, for the purposes of target dependency 
		evaluation. The underlying dependency paths are returned, 
		i.e. a child-first delegation model in cases where pathsets are wrapped 
		inside other pathsets, to ensure that where relevant the target 
		responsible for generating derived resources gets returned as the 
		dependency. 
		
		This method is not for use by targets, and should be called just once 
		during the dependency evaluation phase. 
		
		For pathsets that definitely have no PathSet dependencies, this 
		can be implemented as return ((path, self) for (path, _) in self.resolveWithDestinations(context)). 
		
		Like the other resolve methods, this returns absolute and normalized 
		path strings containing no substitution variables, and ending with a 
		slash for any directories. 
		
		Note that any directory/ items in the returned list indicate
		empty directories to be created; their contents will NOT be
		checked during dependency evaluation, so always use FindPaths if you wish
		to include the contents of a directory. Including non-empty/non-target
		directories is likely to be an error. 
		
		"""
		raise Exception('TODO: must implement _resolveUnderlyingDependencies for %s'%self.__class__)

class __SimplePathSet(BasePathSet):
	""" The most basic PathSet which holds any combination of strings and 
	other PathSets. 
	"""
	def __init__(self, *inputs):

		super(BasePathSet, self).__init__()
		self.contents = flatten(inputs)
		
		self.__location = None
		for x in self.contents:
			if not (isinstance(x, str) or isinstance(x, BasePathSet) or hasattr(x, 'resolveToString')):
				raise BuildException('PathSet may contain only strings, PathSets, Composables, targets and lists - cannot accept %s (%s)'%(x, x.__class__))
		
		self.__location = BuildFileLocation()
		
	def __repr__(self):
		""" Return a string including this class name and the paths from which it was created. """
		return 'PathSet(%s)' % ', '.join('"%s"'%s.replace('\\','/') if isinstance(s, str) else str(s) for s in self.contents)
	
	def __resolveStringPath(self, p, context): # used for anything that isn't a pathset
		if hasattr(p, 'resolveToString'):
			p = p.resolveToString(context)
		
		p = context.getFullPath(p, defaultDir=self.__location, expandList=True)

		for x in p:
			if '*' in x: # sanity check
				raise BuildException('Cannot specify "*" glob patterns here (consider using FindPaths instead): "%s"'%p, location=self.__location)
		# destination is always flat path for things specified absolutely
		# if it's a directory this is a bit inconsistent, but that case doesn't occur so often
		return p, [os.path.basename(x.rstrip('\\/'))+(os.path.sep if isDirPath(x) else '') for x in p]

	def _resolveUnderlyingDependencies(self, context):
		for x in self.contents:
			if not isinstance(x, BasePathSet):
				for item in self.__resolveStringPath(x, context)[0]:
					if '//' in item: # this could easily confuse things later!
						raise BuildException('Invalid path with multiple slashes "%s" in %s'%(item, self), location=self.__location)
					yield item, self
			else:
				# for pathsets, delegate to child
				if len(self.contents)==1:
					# short-circuit this common case, avoiding an extra copy and search
					for item in x._resolveUnderlyingDependencies(context):
						yield item
					return
				for item in x._resolveUnderlyingDependencies(context):
					yield item
		
		# originally we did a duplicates check here, but occasionally you might have a single thing that's 
		# a dependency in more than one way (e.g. a jar that's on the classpath AND packaged within an OSGI bundle)
	
	def resolveWithDestinations(self, context):
		# Docs inherited from base class
		r = []
		for x in self.contents:
			if not isinstance(x, BasePathSet):
				y = self.__resolveStringPath(x, context)
				r.extend(list(zip(y[0], y[1])))
			else:
				if len(self.contents)==1: # short-circuit this common case
					return x.resolveWithDestinations(context)
				r.extend(x.resolveWithDestinations(context))
		return r

NULL_PATH_SET = __SimplePathSet()
"""
A singleton PathSet containing no items. 
"""

def PathSet(*items):
	"""Factory method that creates a single BasePathSet instance containing 
	the specified strings and/or other PathSets. 
	
	An additional composite pathset instance will be constructed to hold them if 
	needed. 
	
	@param items: contains strings, targets and PathSet objects, nested as deeply as 
	you like within lists and tuples. 
	The strings must be absolute paths, or paths relative to the build file 
	where this PathSet is defined, in which case the PathSet must be 
	instantiated during the build file parsing phase (relative paths cannot 
	be used in a PathSet that is instantiated while building or resolving 
	dependencies for a target). 
	Paths may not contain the '*' character, and directory 
	paths must end with an explicit '/'. 
		
	@return: A BasePathSet instance. 
	
	>>> str(PathSet('a', [('b/', PathSet('1/2/3/', '4/5/6/'), ['d/e'])], 'e/f/${x}').resolveWithDestinations(BaseContext({'x':'X/'}))).replace('\\\\\\\\','/')
	"[('BUILD_DIR/a', 'a'), ('BUILD_DIR/b/', 'b/'), ('BUILD_DIR/1/2/3/', '3/'), ('BUILD_DIR/4/5/6/', '6/'), ('BUILD_DIR/d/e', 'e'), ('BUILD_DIR/e/f/X/', 'X/')]"

	>>> str(PathSet('a', [('b/', PathSet('1/2/3/', '4/5/6/'), ['d/e'])], 'e/f/${x}').resolve(BaseContext({'x':'X/'}))).replace('\\\\\\\\','/')
	"['BUILD_DIR/a', 'BUILD_DIR/b/', 'BUILD_DIR/1/2/3/', 'BUILD_DIR/4/5/6/', 'BUILD_DIR/d/e', 'BUILD_DIR/e/f/X/']"
	
	>>> str(PathSet('a', [('b/', PathSet('1/2/3/', '4/5/6/'), ['d/e'])], 'e/f/${x}'))
	'PathSet("a", "b/", PathSet("1/2/3/", "4/5/6/"), "d/e", "e/f/${x}")'

	>>> str([path for (path,pathset) in PathSet('a', [[PathSet('1/2/3/', DirGeneratedByTarget('4/5/6/'), '7/8/')]], DirGeneratedByTarget('9/'))._resolveUnderlyingDependencies(BaseContext({}))]).replace('\\\\\\\\','/')
	"['BUILD_DIR/a', 'BUILD_DIR/1/2/3/', 'BUILD_DIR/4/5/6/', 'BUILD_DIR/7/8/', 'BUILD_DIR/9/']"

	>>> PathSet('a/*').resolve(BaseContext({})) #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
	...
	xpybuild.utils.buildexceptions.BuildException:
	"""
	# This function is called a lot so its performance matters
	
	# Avoid creating a new SimplePathSet if we can
	
	if not items: 
		return NULL_PATH_SET

	if len(items) == 1 and isinstance(items[0], list): # flatten a nested list
		items = items[0]
		if not items: return NULL_PATH_SET
	
	if items[0] is NULL_PATH_SET or items[-1] is NULL_PATH_SET: # common case would be empty at beginning or end
		items = [i for i in items if (i is not NULL_PATH_SET)]
	if len(items) == 1 and isinstance(items[0], BasePathSet): return items[0]
	return __SimplePathSet(items)

		
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
		dir = context.getFullPath(dir, defaultDir=location)
	if not isDirPath(dir):
		raise BuildException('Directory paths must end with an explicit / slash: "%s"'%dir, location=location)
	return dir

class DirBasedPathSet(BasePathSet):
	""" Constructs a pathset using a basedir and a list of (statically defined, 
	non-globbed) basedir-relative paths within it. 
	
	If it is not possible to statically specify the files to be included 
	and globbing is required, use L{FindPaths} instead to perform a dynamic 
	search; but since FindPaths is a lot slower due to the additional file 
	system operations it is better to use DirBasedPathSet where possible. 
		
	e.g. DirBasedPathSet('${MY_DIR}/', 'a', 'b/', '${MY_JARS[]}', 'x, y, ${Z[]}')
	
	>>> str(DirBasedPathSet('${MY_DIR}', 'a', 'b/c/', '${MY_JARS[]}', 'd').resolveWithDestinations(BaseContext({'MY_DIR':'MY_DIR/', 'MY_JARS[]':'  1 , 2/3, 4/5/'}))).replace('\\\\\\\\','/')
	"[('BUILD_DIR/MY_DIR/a', 'a'), ('BUILD_DIR/MY_DIR/b/c/', 'b/c/'), ('BUILD_DIR/MY_DIR/1', '1'), ('BUILD_DIR/MY_DIR/2/3', '2/3'), ('BUILD_DIR/MY_DIR/4/5/', '4/5/'), ('BUILD_DIR/MY_DIR/d', 'd')]"

	>>> DirBasedPathSet('mydir', 'a*b').resolve(BaseContext({})) #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
	...
	xpybuild.utils.buildexceptions.BuildException:

	>>> str(PathSet('a', DirBasedPathSet(DirGeneratedByTarget('4/5/6/'), '7/8')))
	'PathSet("a", DirBasedPathSet(DirGeneratedByTarget("4/5/6/"), [\\'7/8\\']))'
	
	>>> str([path for (path,pathset) in PathSet('a', DirBasedPathSet(DirGeneratedByTarget('4/5/6/'), '7/8'))._resolveUnderlyingDependencies(BaseContext({}))]).replace('\\\\\\\\','/')
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
		self.__location = BuildFileLocation()
	
	def __repr__(self):
		""" Return a string including this class name and the basedir and child paths from which it was created. """
		return 'DirBasedPathSet(%s, %s)' % (self.__dir, self.__children)

	def _resolveUnderlyingDependencies(self, context):
		if isinstance(self.__dir, BaseTarget):
			return [self.__dir.resolveToString(context), self] 
		elif isinstance(self.__dir, BasePathSet):
			return self.__dir._resolveUnderlyingDependencies(context)
		else:
			return ((abspath, self) for abspath, dest in self.resolveWithDestinations(context))
	
	def resolveWithDestinations(self, context):
		children = flatten([
			[s.strip() for s in context.expandPropertyValues(c, expandList=True)]
			for c in self.__children])

		dir = _resolveDirPath(self.__dir, context, self.__location)
		
		result = []
		for c in children:

			if '*' in c: 
				raise BuildException('Cannot specify "*" patterns here (consider using FindPaths instead): "%s"'%c, location=self.__location)
			if os.path.isabs(c):
				raise BuildException(f'Cannot specify absolute path "{c}", as all paths must be relative to the base directory {self.__dir}; (hint: consider using the xpybuild.propertysupport.basename(), and check for unintentional leading slashes)', location=self.__location)

			isdir = isDirPath(c)

			c=os.path.join(context.expandPropertyValues(dir), c)
			c=os.path.normpath(c.rstrip('\\/'+os.path.sep))

			if isdir: c = c+os.path.sep

			result.append( ( c, c[len(dir):] ) )
		return result
		

class FindPaths(BasePathSet):
	""" A lazily-evaluated PathSet that uses ``*`` and ``**`` (ant-style) globbing 
	to dynamically discover files (and optionally directories) under a common 
	parent directory. 
	
	As FindPaths performs a dynamic search of the file system during the dependency 
	checking phase of each build it is considerably slower than other PathSets, 
	so should only be used for specifying the contents of a directory with lots of entries 
	or a file or directory where it is not possible to statically specify the filenames in the build 
	script - for which cases always use `PathSet` or `DirBasedPathSet` instead. 
	
	FindPaths matching is always case-sensitive, will give an error if the dir does not exist 
	or any of the includes fail to match anything. Sorts its output to ensure 
	determinism. 
	
	Includes/excludes are specified using ``*`` and ``**`` wildcards (similar to ant), 
	where ``*`` represents any path element and ``**`` represents zero or more path 
	elements. Path elements may not begin with a slash, or contain any 
	backslash characters. They match paths underneath the base dir.
	
	Each include/exclude applies either to files OR directories, depending on 
	whether it ends with a ``/``. File include/excludes (e.g. ``foo/**``) are the 
	most common (and the file ``**`` pattern is the default include if none is 
	specified). But if used for a target such as a Copy, note that empty 
	directories will NOT be returned by file patterns, so if you wish to 
	copy all empty directories as well as all files, use:: 

		FindPaths(..., includes=['**', '**/']). 

	Destination paths (where needed) are generated from the path underneath the
	base dir.

	FindPaths will return file or directory symlinks (with ``/`` suffix if directory), 
	but will not recurse into directory symlinks. 
	
	@param dir: May be a simple string, or a DirGeneratedByTarget to glob under a 
	directory generated as part of the build. To find paths from a set of 
	targets use dir=TargetsWithinDir (though only use this when that dynamism 
	is required, as this will be slower than statically listing the targets 
	individually or using TargetsWithTag). 

	>>> str(FindPaths('a/b/c', includes=['*.x', 'y/**/z/foo.*'], excludes=['xx', '**/y']))
	'FindPaths("a/b/c", includes=["*.x", "y/**/z/foo.*"], excludes=["xx", "**/y"])'

	>>> str(PathSet('a', FindPaths(DirGeneratedByTarget('4/5/6/'), includes='*.xml')))
	'PathSet("a", FindPaths(DirGeneratedByTarget("4/5/6/"), includes=["*.xml"], excludes=[]))'
	
	>>> FindPaths('x', includes=['*.x', 'c:\\d'], excludes=[])#doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
	...
	xpybuild.utils.buildexceptions.BuildException:

	>>> FindPaths('x', includes=['*.x', '${foo}'], excludes=[])#doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
	...
	xpybuild.utils.buildexceptions.BuildException:

	"""
	
	_skipDependenciesExistenceCheck = True # since we only return items we've found on disk, no need to check them again
	
	_shortcutUptodateCheck = IS_WINDOWS # on Windows os.scandir can efficiently get the stat results without an extra call
	
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
			
		if not self.includes: 
			self.includes = None # comparing to None is very efficient
		else:
			self.includes = GlobPatternSet.create(self.includes)

		if not self.excludes: 
			self.excludes = None
		else:
			self.excludes = GlobPatternSet.create(self.excludes)
			
		if isinstance(dir, str) and '\\' in dir: # avoid silly mistakes, and enforce consistency
			raise BuildException('Invalid base directory for FindPaths - must not contain \\ (always use forward slashes)')
		
		self.location = BuildFileLocation()
		self.__lock = threading.Lock()
		self.__cached = None
	
	def __repr__(self): 
		""" Return a string including this class name and the basedir and include/exclude patterns with which it was created. """
		return ('FindPaths(%s, includes=%s, excludes=%s)'%('"%s"'%self.__dir if isinstance(self.__dir, str) else str(self.__dir), self.includes or [], self.excludes or [])).replace('\'','"')
	
	def _resolveUnderlyingDependencies(self, context):
		if isinstance(self.__dir, BaseTarget):
			return [self.__dir.resolveToString(context), self] 
		elif isinstance(self.__dir, BasePathSet): 
			return self.__dir._resolveUnderlyingDependencies(context)
		else:
			return ((abspath, self) for abspath, dest in self.resolveWithDestinations(context))
		
	@staticmethod
	def __removeNamesFromList(l, toberemoved):
		"""
		Efficiently removes all items in toberemoved from list l (in-place). 
		
		@param toberemoved: must contain only items from l, with no duplicates. 
		"""	
		if len(toberemoved)==0: return
		if len(toberemoved) == len(l): 
			l[:] = []
		elif len(toberemoved) > 2: toberemoved = set(toberemoved)
		l[:] = [x for x in l if (x not in toberemoved)]
	
	def resolveWithDestinations(self, context):
		"""
		Uses the file system to returns a list of relative paths for files 
		matching the specified include/exclude patterns, throwing a 
		BuildException if none can be found. 

		This method will cache its result after being called the first time. 
		
		Note that it is possible the destinations may contain "../" elements - 
		targets for which that could be a problem should check for and disallow 
		such destinations (e.g. for copy we would not want to allow copying to 
		destinations outside the specified root directory). 
		
		"""
		log = logging.getLogger('FindPaths')
		log.debug('FindPaths resolve starting for: %s', self)
		with self.__lock:
			_shortcutUptodateCheck = self._shortcutUptodateCheck
			newestTimestamp, newestFile = 0, None
			
			# think this operation is atomically thread-safe due to global interpreter lock
			if self.__cached: return self.__cached
			
			# resolve dir if needed, relative to where the fileset was specified in the build file
			
			resolveddir = _resolveDirPath(self.__dir, context, self.location)

			matches = []
			try:
				if not os.path.isdir(resolveddir):
					raise BuildException('FindPaths root directory does not exist: "%s"'%os.path.normpath(resolveddir), location=self.location)
				startt = time.time()
				if self.includes is not None:
					unusedPatternsTracker = GlobUnusedPatternTracker(self.includes) # give an error if any are not used
				else:
					unusedPatternsTracker = None
					
				visited = 0
				scanroot = normLongPath(resolveddir)[:-1]
				pathsToWalk = [scanroot] # stack of paths
				while len(pathsToWalk)>0:
					visited += 1 
					longdir = pathsToWalk.pop()
					root = longdir[len(scanroot):].replace('\\','/').strip('/')
					if root != '': root += '/'
					#log.debug('visiting: "%s"'%root)

					# emulate os.walk's API, since we think it's more efficient to glob all the paths in a given root dir at the same time
					with os.scandir(longdir) as it:
						dirs = []
						files = []
						filetimes = {}
						symlinks = None # set to keep track of symlinks, to avoid recursing into them
						for entry in it:
							if entry.is_dir():
								dirs.append(entry.name)
								if entry.is_symlink():
									if symlinks is None: 
										symlinks = {entry.name}
									else:
										symlinks.add(entry.name)
							else:
								files.append(entry.name)
								if _shortcutUptodateCheck:
									filetimes[entry.name] = entry.stat().st_mtime
						entry = None
					
						# optimization: if this doesn't require walking down the dir tree, don't do any!
						# (this optimization applies to includes like prefix/** but not if there is a bare '**' 
						# in the includes list)
						if self.includes is not None:
							self.includes.removeUnmatchableDirectories(root, dirs)
						
						# optimization: if there's an exclude starting with this dir and ending with '/**' or '/*', don't navigate to it
						# we deliberately match only against filename patterns (not dir patterns) since 
						# empty dirs are handled in the later loop not through this mechanism, so it's just files that matter
						if self.excludes is not None and dirs != []:
							# nb: both dirs and the result of getPathMatches will have no trailing slashes
							self.__removeNamesFromList(dirs, self.excludes.getPathMatches(root, filenames=dirs))

						# any other subdirs will need to be walked to
						for dir in dirs:
							if symlinks is not None and dir in symlinks: continue # don't recursive into symlinks (messes up copying)
							pathsToWalk.append(longdir+os.sep+dir)
						dir = None
						
						# now find which files and empty dirs match
						matchedemptydirs = dirs
						
						if self.includes is not None:
							files, matchedemptydirs = self.includes.getPathMatches(root, filenames=files, dirnames=matchedemptydirs, unusedPatternsTracker=unusedPatternsTracker)
						else:
							matchedemptydirs = [] # only include empty dirs if explicitly specified
						
						if self.excludes is not None:
							exfiles, exdirs = self.excludes.getPathMatches(root, filenames=files, dirnames=matchedemptydirs)
							self.__removeNamesFromList(files, exfiles)
							self.__removeNamesFromList(matchedemptydirs, exdirs)
							
						for p in files:
							matches.append(root+p)
						if _shortcutUptodateCheck:
							for p in files:
								thisTimestamp = filetimes[p]
								# main thing is to compare the timestamp, but if there's a tie then pick the lexical latest filename, 
								# which is better than being file-system-non-deterministic
								if thisTimestamp > newestTimestamp or (thisTimestamp == newestTimestamp and newestFile is not None and root+p > newestFile):
									newestTimestamp, newestFile = thisTimestamp, str(self.__dir)+root+p
							
						for p in matchedemptydirs:
							matches.append(root+p+'/')					
				
				#end while
				if _shortcutUptodateCheck:
					self._newestFile = newestTimestamp, newestFile

				log.info('FindPaths in "%s" found %d path(s) for %s after visiting %s directories; %s', resolveddir, len(matches), self, visited, self.location)
				if time.time()-startt > 5: # this should usually be pretty quick, so may indicate a real build file mistake
					log.warn('FindPaths took a long time: %0.1f s to evaluate %s; see %s', time.time()-startt, self, self.location)
				
				if not matches:
					raise BuildException('No matching files found', location=self.location)
				if unusedPatternsTracker is not None:
					unusedPatterns = unusedPatternsTracker.getUnusedPatterns()
					if unusedPatterns != []:
						raise BuildException('Some include patterns did not match any files: %s'%', '.join(unusedPatterns), location=self.location)
						
			except BuildException as e:
				raise BuildException('%s for %s'%(e.toSingleLineString(target=None), self), causedBy=False, location=self.location)
			except Exception as e:
				raise BuildException('%s for %s'%(repr(e), self), causedBy=True, location=self.location)
			
			result = []
			normedbasedir = normpath(resolveddir)
			replacesep = os.sep != '/'
			for m in matches:
				if replacesep and '/' in m: m = m.replace('/', os.sep)
				
				result.append( ( normedbasedir+m, m ) )
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
	
	See also L{TargetsWithinDir}.
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
		self.__location = BuildFileLocation()
		self.__allowDirectories = allowDirectories or walkDirectories
		self.__walkDirectories = walkDirectories
	
	def __repr__(self):
		""" Return a string including this class name and the tag it's looking up. """
		return 'TargetsWithTag(%s, allowDirectories=%s)' % (self.__targetTag, self.__allowDirectories)
	
	def resolveWithDestinations(self, context):
		log = logging.getLogger('TargetsWithTag')
		try:
			targets = context.getTargetsWithTag(self.__targetTag)
		except BuildException as e: # add location info to exception
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
		except BuildException as e: # add location info to exception
			raise BuildException(str(e), location=self.__location)
		if len(targets)==0: raise BuildException('No targets have tag "%s"'%self.__targetTag, location=self.__location)
		return ( (t.path, self) for t in targets)


class TargetsWithinDir(BasePathSet):
	"""
	A special PathSet that resolves to all build target output paths that are
	descendents of the specified parent dir (which is not a target itself, 
	but somewhere under a build output directory). When resolved, this 
	pathset returns a single source and destination path which is the parent 
	directory itself. 
	
	This PathSet can be wrapped in FindPaths if the contained files and 
	directories are needed. 
	
	See also L{TargetsWithTag}.

	"""
	def __init__(self, parentDir):
		"""
		@param parentDir: a string identifying the parent dir. When resolved, 
		must end in a slash. 
		
		"""
		self.__parentDir = parentDir
		self.__location = BuildFileLocation()
	
	def __repr__(self):
		return 'TargetsWithinDir(%s)' % (self.__parentDir)
	
	def __getDir(self, context):
		dir = context.getFullPath(self.__parentDir, defaultDir=self.__location)
		if not isDirPath(dir):
			raise BuildException('Directory paths must end with a slash: "%s"'%dir, location=self.__location)
		return dir
	def resolveWithDestinations(self, context):
		dir = self.__getDir(context)
		return [(dir, os.path.basename(dir))]
	def _resolveUnderlyingDependencies(self, context):
		dir = self.__getDir(context)
		found = 0
		for targetpath in context._getTargetPathsWithinDir(dir):
			found += 1
			yield targetpath, self
		if found == 0:
			raise BuildException('TargetsWithinDir found no targets under parent directory "%s" (%s)'%(self.__parentDir, dir), location=self.__location)

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
	
	>>> str([path for (path,pathset) in PathSet('a', FilteredPathSet(isDirPath, DirGeneratedByTarget('4/5/6/')))._resolveUnderlyingDependencies(BaseContext({}))]).replace('\\\\\\\\','/')
	"['BUILD_DIR/a', 'BUILD_DIR/4/5/6/']"

	>>> str([path for (path,pathset) in PathSet('a', FilteredPathSet(lambda p:p.endswith('.java'), FindPaths(DirGeneratedByTarget('4/5/6/'))))._resolveUnderlyingDependencies(BaseContext({}))]).replace('\\\\\\\\','/')
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
		return result if self.__delayFiltration else ((src, self) for (src, _) in result if isDirPath(src) or self.__includeDecider(src))

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
	
	Do not use this pathset for adding a prefix to the destinations - for that 
	L{AddDestPrefix} is a better solution. 
	
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
		not backslashes) as input, and returns a potentially different dest path. 
		If possible, use a named function rather than a lamba. 
		"""
		if not isinstance(pathSet, BasePathSet): pathSet = PathSet(pathSet)
		_DerivedPathSet.__init__(self, pathSet)
		self.__fn = fn
	
	def __repr__(self):
		return 'MapDest(%s, %s)' % (self.__fn.__name__, self._pathSet)
	
	def resolveWithDestinations(self, context):
		result = self._pathSet.resolveWithDestinations(context)
		return [(key, os.path.normpath(context.expandPropertyValues(self.__fn(value.replace('\\','/'))))+(os.path.sep if isDirPath(key) else '')) for (key,value) in result]

class MapDestFromSrc(_DerivedPathSet):
	""" Applies a functor to the src paths of the enclosed PathSet to get new destinations
	(the PathSet's source paths are unaffected)
	
	Note that paths passed to the functor will always have forward slashes. 

	e.g. MapDestFromSrc(lambda x:x.lower(), mypathset)
	
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
		return 'MapDestFromSrc(%s, %s)' % (self.__fn.__name__, self._pathSet)
	
	def resolveWithDestinations(self, context):
		result = self._pathSet.resolveWithDestinations(context)
		return [(key, os.path.normpath(context.expandPropertyValues(self.__fn(key.replace('\\','/'))))+(os.path.sep if isDirPath(key) else '')) for (key,value) in result]

MapSrc = MapDestFromSrc
"""
Legacy name for MapDestFromSrc. 
"""

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
	xpybuild.utils.buildexceptions.BuildException: Cannot strip 1 parent dir(s) from "a" as it does not have that many parent directories

	>>> str(RemoveDestParents(1, DirBasedPathSet('mydir/', 'b/')).resolveWithDestinations(BaseContext({}) )).replace('\\\\\\\\','/')
	Traceback (most recent call last):
	...
	xpybuild.utils.buildexceptions.BuildException: Cannot strip 1 parent dir(s) from "b/" as it does not have that many parent directories

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
		if isinstance(self.newDestRelPath, str): assert '\\' not in self.newDestRelPath
	
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
		assert isinstance(dirTargetName, str)
		assert dirTargetName.endswith('/')
		self.__target = dirTargetName
		self.__location = BuildFileLocation()
		
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
		return ((abspath, self) for abspath, dest in self.resolveWithDestinations(context))

	def resolveWithDestinations(self, context):
		t = context.getFullPath(self.__target, defaultDir=self.__location)
		return [(t, os.path.basename(t.strip('/\\'))+(os.path.sep if isDirPath(t) else '') )]

	def __add__(self, suffix):
		# suffix is probably a string but might be a Composable/callable
		return DirBasedPathSet(self, suffix)

from xpybuild.basetarget import BaseTarget

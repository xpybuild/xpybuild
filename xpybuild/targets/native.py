# xpyBuild - eXtensible Python-based Build System
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
# $Id: native.py 301527 2017-02-06 15:31:43Z matj $
#

"""
Contains targets for compiling C and C++, and linking the resulting object files 
into a library or executable. 

Also contains functors for adding the necessary suffix/prefix for these targets 
on the current platform:

.. autosummary::
	exename
	objectname
	libname
	staticlibname
	
"""

import os, inspect, re, string, time
import datetime

from xpybuild.buildcommon import *
from xpybuild.basetarget import BaseTarget
from xpybuild.propertysupport import defineOption, Composable
from xpybuild.utils.functors import makeFunctor
from xpybuild.utils.process import call
from xpybuild.pathsets import PathSet, BasePathSet
from xpybuild.buildcontext import getBuildInitializationContext
from xpybuild.utils.buildexceptions import BuildException
from xpybuild.utils.fileutils import openForWrite, mkdir, deleteFile, cached_getmtime, cached_exists, toLongPathSafe, cached_stat

class __CompilersNotSpecified(object):
	def __getattr__(self, attr):
		raise Exception('Cannot use native targets until a compiler is configured by setting the native.compilers option')
	def __repr__(self): return '<native.compilers option is not configured>'

# these options all need documenting
defineOption('native.compilers', __CompilersNotSpecified())
defineOption('native.libs', [])
defineOption('native.libpaths', [])
defineOption('native.c.flags', None) # defaults to native.cxx.flags if not set
defineOption('native.cxx.flags', [])
defineOption('native.cxx.path', [])

defineOption('native.include', [])
"""List of include dirs to be added (each ending in a slash). 
"""
defineOption('native.include.upToDateCheckIgnoreRegex', '') 
"""Any include files which this regular expression matches are ignored for dependency checking purposes. 
This can be used to speed up up-to-date checking by avoiding locations whose contents never change. 
However be careful not to put any paths that might change into this regular expression, 
otherwise your targets may not rebuild as expected when their dependencies change.
Paths must use forward slashes no backslashes for separating directories. 
 """
defineOption('native.include.upToDateCheckIgnoreSystemHeaders', False) 
"""Include files located in (or referenced from) system header directories are ignored 
for dependency checking purposes; only user header files are included. 
This can be used to speed up up-to-date checking as typically system headers rarely 
if ever change. 
"""

defineOption('native.link.flags', [])

if IS_WINDOWS:
	defineOption('native.cxx.exenamefn', FilenameStringFormatter("%s.exe"))
	defineOption('native.cxx.libnamefn', FilenameStringFormatter("%s.dll"))
	defineOption('native.cxx.staticlibnamefn', FilenameStringFormatter("%s.lib"))
	defineOption('native.cxx.objnamefn', FilenameStringFormatter("%s.obj"))
else:
	defineOption('native.cxx.exenamefn', FilenameStringFormatter("%s"))
	defineOption('native.cxx.libnamefn', FilenameStringFormatter("lib%s.so"))
	defineOption('native.cxx.staticlibnamefn', FilenameStringFormatter("lib%s.a"))
	defineOption('native.cxx.objnamefn', FilenameStringFormatter("%s.o"))

class _AddTrailingDirectorySlashesPathSet(BasePathSet):
	""" NOT for use in builds. 
	
	Adds missing slashes to the source and underlying dependencies 
	(unless the basename contains a dot, suggesting it's a file from a TargetsWithinDir). 
	
	For use in builds before 1.15 that incorrectly omitted slashes for include 
	directories. 
	"""
	def __init__(self, pathSet):
		self._pathSet = pathSet
	
	def __repr__(self):
		return 'AddTrailingSlashPathSet(%s)' % (self._pathSet)
	
	def resolveWithDestinations(self, context):
		return [((src if isDirPath(src) else src+os.path.sep), dest) for src,dest in self._pathSet.resolveWithDestinations(context)]
	def _resolveUnderlyingDependencies(self, context):
		# this is a heuristic - try to avoid adding slashes to TargetsWithinDir(...) .h files
		return (((src if isDirPath(src) or '.h' in os.path.basename(src) else src+os.path.sep), pathset) for src,pathset in self._pathSet._resolveUnderlyingDependencies(context))

class Cpp(BaseTarget):
	""" Target that compiles a C++ source file to a single object file. 
	"""
	
	__rebuild_makedepend_count = 0

	def __init__(self, object, source, includes=None, flags=None, dependencies=None, options=None):
		"""
		@param object: the object file to generate; see L{objectname}.
		@param source: a (list of) source files
		
		@param includes: a (list of) include directories, as strings or PathSets, 
			each with a trailing slash; the directories in the `native.include` 
			option are also added.
			
			If this target depends on some include files that are generated by another target, 
			make sure it's a directory target since all include directories must either 
			exist before the build starts or be targets themselves. 
			If specifying a subdirectory of a generated directory, do this using DirGeneratedByTarget. 
			If you have a composite generated directory made up of several 
			file targets, wrap them in TargetsWithinDir before passing as the includes parameter. 
		
		@param flags: a list of compiler flags in addition to those in the 
			`native.cxx.flags`/`native.c.flags` option. 
		
		@param dependencies: a list of additional dependencies that need to be built 
			before this target. Usually this is not needed. 
		
		@param options: DEPRECATED; use .option() instead
		"""
		self.source = PathSet(source)
		
		# currently we don't bother adding the native include dirs here as they're probably always going to be there
		# for time being, explicitly cope with missing slashes, though really build authors should avoid this
		self.includes = _AddTrailingDirectorySlashesPathSet(PathSet(includes))
		self.flags = flatten([flags]) or []
		
		# nb: do not include any individual header files in main target deps even if we've already 
		# got cached makedepends from a previous build, 
		# because it's possible they are no longer needed and no longer exist (and we don't want spurious 
		# build failures); this also has the advantage that it doesn't enlarge and slow down the stat cache 
		# during dep resolution of non-native targets, since it'll only be populated once we're into 
		# the up to date checking phase
		
		BaseTarget.__init__(self, object, PathSet([dependencies, source, self.includes]))
		
		for k,v in (options or {}).items(): self.option(k, v)
		self.tags('native')
	
	def run(self, context):
		options = self.options

		mkdir(os.path.dirname(self.path))
		options['native.compilers'].cxxcompiler.compile(context, output=self.path, options=options, 
			flags=self._getCompilerFlags(context), 
			src=self.source.resolve(context), 
			includes=self._getIncludeDirs(context)
			)

	def clean(self, context):
		deleteFile(self._getMakeDependsFile(context))
		BaseTarget.clean(self, context)

	def _getMakeDependsFile(self, context):
		# can only be called after target resolution, when workdir is set
		return toLongPathSafe(context.getPropertyValue("BUILD_WORK_DIR")+'/targets/makedepend-cache/'+os.path.basename(self.workDir)+'.makedepend')

	def _getCompilerFlags(self, context):
		return flatten(self.getOption('native.cxx.flags')+[context.expandPropertyValues(x).split(' ') for x in self.flags])
	
	def _getIncludeDirs(self, context):
		return self.includes.resolve(context)+flatten([context.expandPropertyValues(x, expandList=True) for x in self.getOption('native.include')])

	def getHashableImplicitInputs(self, context):	
		r = super(Cpp, self).getHashableImplicitInputs(context)

		r.append('compiler flags: %s' % self._getCompilerFlags(context))
		
		# this will provide a quick way to notice changes such as TP library version number changed etc
		# and also is the only way we'll detect the need to rebuild for includes that are regex'd out
		includedirs = self._getIncludeDirs(context)
		for path in includedirs:
			r.append('include dir: '+os.path.normcase(path))
		
		# This is called exactly once during up-to-date checking OR run, which 
		# means we will have generated all target dependencies 
		# (e.g. include files, source files etc) by this point
		
		# Since non-target include files won't be known until this point, we need 
		# to perform up-to-date-ness checking for them here (rather than in 
		# targetwrapper as normally happens for dependencies). 
		
		startt = time.time()

		try:
			targetmtime = os.stat(self.path).st_mtime # must NOT use getstat cache, don't want to pollute it with non-existence
		except os.error: # file doesn't exist
			targetmtime = 0

		makedependsfile = self._getMakeDependsFile(context)
		if targetmtime != 0 and not os.path.exists(makedependsfile):  # no value in using stat cache for this, not used elsewhere
			targetmtime = 0 # treat the same as if target itself didn't exist
		
		newestFile, newestTime = None, 0 # keep track of the newest source or include file
		
		if IS_WINDOWS: # normalizes case for this OS but not slashes (handy for regex matching)
			def xpybuild_normcase(path):
				return path.lower()
		else:
			def xpybuild_normcase(path):
				return path
		
		# changes in these options must cause us to re-execute makedepends
		ignoreregex = self.options['native.include.upToDateCheckIgnoreRegex']
		if ignoreregex: 
			ignoreregex = xpybuild_normcase(ignoreregex)
			r.append('option native.include.upToDateCheckIgnoreRegex=%s'%ignoreregex)
		makedependsoptions = "upToDateCheckIgnoreRegex='%s', upToDateCheckIgnoreSystemHeaders=%s, flags=%s"%(
			ignoreregex,
			self.options['native.include.upToDateCheckIgnoreSystemHeaders'],
			self._getCompilerFlags(context), 
			)

		# first, figure out if we need to (re-)run makedepends or can use the cached info from the last build
		runmakedepends = False
		
		if targetmtime == 0:
			runmakedepends = True
		
		alreadychecked = set() # paths that we've already checked the date of
		sourcepaths = []
		for path, _ in self.source.resolveWithDestinations(context):
			mtime = cached_getmtime(path)
			alreadychecked.add(path)
			sourcepaths.append(path)
			if mtime > newestTime: newestFile, newestTime = path, mtime
		if newestTime > targetmtime: runmakedepends = True
		
		if (not runmakedepends) and os.path.exists(makedependsfile): # (no point using stat cache for this file)
			# read file from last time; if any of the transitive dependencies 
			# have changed, we should run makedepends again to update them
			with io.open(makedependsfile, 'r', encoding='utf-8') as f:
				flags = f.readline().strip()
				if flags != makedependsoptions:
					runmakedepends = True
				else:
					for path in f:
						path = path.strip()
						pathstat = cached_stat(path, errorIfMissing=False)
						if pathstat is False:
							# file doesn't exist - must rebuild
							runmakedepends = True
							(self.log.critical if Cpp.__rebuild_makedepend_count <= 5 else self.log.info)(
								'Recalculating C/C++ dependencies of %s as dependency no longer exists: %s', self, newestFile)

							break
						mtime = pathstat.st_mtime
						alreadychecked.add(path)
						if mtime > newestTime: newestFile, newestTime = path, mtime
						
			if newestTime > targetmtime: runmakedepends = True
		
		# (re-)run makedepends
		if runmakedepends:
			# only bother to log if we're recalculating
			if targetmtime != 0: 
				Cpp.__rebuild_makedepend_count += 1 # log the first few at crit
				(self.log.critical if Cpp.__rebuild_makedepend_count <= 5 else self.log.info)(
					'Recalculating C/C++ dependencies of %s; most recently modified dependent file is %s at %s', self, newestFile, 
						datetime.datetime.fromtimestamp(newestTime).strftime('%a %Y-%m-%d %H:%M:%S'))

			try:
				makedependsoutput = self.options['native.compilers'].dependencies.depends(
					context=context, 
					src=sourcepaths, 
					options=self.options, 
					flags=self._getCompilerFlags(context), 
					includes=includedirs,
					)
			except Exception as ex:
				raise BuildException('Dependency resolution failed for %s'%(sourcepaths[0]), causedBy=True)
			
			# normalize case to avoid problems on windows, and strip out sources since we already checked them above
			makedependsoutput = [os.path.normcase(path) for path in makedependsoutput if path not in sourcepaths]
			makedependsoutput.sort()
			if ignoreregex:
				ignoreregex = re.compile(ignoreregex)
				# match against version of path with forward slashes because making a regex with backslashes is a pain and not cross-platform
				makedependsoutput = [path for path in makedependsoutput if not ignoreregex.match(path.replace(os.sep, '/'))]

			# find the newest time from these files; if this is same as previous makedepends, won't do anything
			for path in makedependsoutput:
				if path in alreadychecked: continue
				mtime = cached_getmtime(path)
				if mtime > newestTime: newestFile, newestTime = path, mtime
			
			# write out new makedepends file for next time
			mkdir(os.path.dirname(makedependsfile))
			assert '\n' not in makedependsoptions, makedependsoptions # sanity check
			with io.open(makedependsfile, 'w', encoding='utf-8') as f:
				f.write(makedependsoptions)
				f.write('\n')
				for path in makedependsoutput:
					f.write('%s\n'%path)

		# endif runmakedepends
		
		# include the newest timestamp as an implicit input, so that we'll rebuild if any include files have changed
		# no need to log this, as targetwrapper already logs differences in implicit inputs
		if newestFile is not None:
			newestDateTime = datetime.datetime.fromtimestamp(newestTime)
			r.append('newest dependency was modified at %s.%03d: %s'%(
				newestDateTime.strftime('%a %Y-%m-%d %H:%M:%S'), 
				newestDateTime.microsecond/1000, 
				os.path.normcase(newestFile)))

		if time.time()-startt > 5: # this should usually be pretty quick, so if it takes a while it may indicate a real build file mistake
			self.log.warn('C/C++ dependency generation took a long time: %0.1f s to evaluate %s', time.time()-startt, self)
		
		return r
		
class C(Cpp):
	""" Target that compiles a C source file to a single object file. 
	"""
	
	# identical to Cpp except for actual run method
	
	def run(self, context):
		options = self.options
		mkdir(os.path.dirname(self.path))
		options['native.compilers'].ccompiler.compile(context, output=self.path,
				options=options, 
				flags=self._getCompilerFlags(context), 
				src=self.source.resolve(context),
				includes=self._getIncludeDirs(context)
				)
		
	def _getCompilerFlags(self, context):
		return flatten(
			(self.options['native.c.flags'] or self.options['native.cxx.flags'])
			+[context.expandPropertyValues(x).split(' ') for x in self.flags])

		
class Link(BaseTarget):
	""" Target that links object files (typically generated by `Cpp` or `C`) to an 
	executable or library binary. 
	"""
	
	def __init__(self, bin, objects, libs=None, libpaths=None, shared=False, options=None, flags=None, dependencies=None):
		"""
		@param bin: the output binary. See L{exename}, L{libname}, L{staticlibname}. 

		@param objects: a (list of) input object

		@param libs: a (list of) libraries linked against (optional) in platform-neutral format. 
		Can include list properties like '${FOO_LIB_NAMES[]}'. 

		@param libpaths: a (list of) additional library search directories (optional)

		@param shared: if true compiles to a shared object (.dll or .so) (optional, defaults to false)

		@param flags: a list of additional linker flags

		@param options: [DEPRECATED - use .option() instead]

		@param dependencies: a list of additional dependencies (targets or files)
		"""
		self.objects = PathSet(objects)
		self.libs = libs or []
		self.libpaths = PathSet(libpaths or [])
		self.shared=shared
		self.flags = flags or []
		BaseTarget.__init__(self, bin, PathSet(self.objects, (dependencies or [])))
		for k,v in (options or {}).items(): self.option(k, v)
		
		self.tags('native')
	
	def run(self, context):
		options = self.options

		mkdir(os.path.dirname(self.path))
		options['native.compilers'].linker.link(context, output=self.path,
				options=options, 
				flags=options['native.link.flags']+self.flags, 
				shared=self.shared,
				src=self.objects.resolve(context),
				libs=flatten([(y.strip() for y in context.expandPropertyValues(x, expandList=True)) for x in self.libs+options['native.libs'] if x]),
				libdirs=flatten(self.libpaths.resolve(context)+[context.expandPropertyValues(x, expandList=True) for x in options['native.libpaths']]))

	def getHashableImplicitInputs(self, context):
		r = super(Link, self).getHashableImplicitInputs(context)
		
		options = self.options
		r.append('libs: '+context.expandPropertyValues(str(self.libs+options['native.libs'])))
		r.append('libpaths: '+context.expandPropertyValues(str(self.libpaths)))
		r.append('native.libpaths: %s'%options['native.libpaths'])
		r.append('shared: %s, flags=%s'%(self.shared, self.flags))
		
		return r
		
class Ar(BaseTarget):
	""" Target that compiles .a archive files from collections of object files. 
	"""
	
	def __init__(self, bin, objects):
		"""
		@param bin: the output library

		@param objects: a (list of) input objects

		"""
		self.objects = PathSet(objects)
		BaseTarget.__init__(self, bin, self.objects)
		self.tags('native')
	
	def run(self, context):
		options = self.options

		mkdir(os.path.dirname(self.path))
		options['native.compilers'].archiver.archive(context, output=self.path,
				options=options,
				src=self.objects.resolve(context))

	def getHashableImplicitInputs(self, context):
		r = super(Ar, self).getHashableImplicitInputs(context)
		
		r.append('objects: %s'%self.objects)
		
		return r
		
exename = makeFunctor(lambda c, i:c.getGlobalOption('native.cxx.exenamefn')(c.expandPropertyValues(i)), name='exename')
"""Functor that adds the suffix/prefix for an executable to a path (using the `native.cxx.exenamefn` option for this platform), for example: 
	`Link(exename('${OUTPUT_DIR}/myprogram'), ...)`
"""
objectname = makeFunctor(lambda c, i:c.getGlobalOption('native.cxx.objnamefn')(c.expandPropertyValues(i)), name='objectname')
"""Functor that adds the suffix/prefix for a C/C++ object file to a path (using the `native.cxx.objnamefn` option for this platform), for example: 
	`Cpp(objectname('${OUTPUT_DIR}/cpp_objects/myfile'), ...)`
"""
libname = makeFunctor(lambda c, i:c.getGlobalOption('native.cxx.libnamefn')(c.expandPropertyValues(i)), name='libname')
"""Functor that adds the suffix/prefix for a dynamic library to a path (using the `native.cxx.libnamefn` option for this platform), for example: 
	`Link(libname('${OUTPUT_DIR}/mylibrary'), ...)`
"""
staticlibname = makeFunctor(lambda c, i:c.getGlobalOption('native.cxx.staticlibnamefn')(c.expandPropertyValues(i)), name='staticlibname')
"""Functor that adds the suffix/prefix for a static library to a path (using the `native.cxx.staticlibnamefn` option for this platform), for example: 
	`Link(staticlibname('${OUTPUT_DIR}/mylibrary'), ...)`
"""

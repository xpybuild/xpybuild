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
@undocumented: _AddTrailingDirectorySlashesPathSet
"""

import os, inspect, re, string, time
import datetime

from buildcommon import *
from basetarget import BaseTarget
from propertysupport import defineOption
from utils.process import call
from pathsets import PathSet, BasePathSet
from buildcontext import getBuildInitializationContext
from buildexceptions import BuildException
from propertyfunctors import make_functor, Composable
from utils.fileutils import openForWrite, mkdir, deleteFile, getmtime, exists, toLongPathSafe, getstat

class __CompilersNotSpecified(object):
	def __getattr__(self, attr):
		raise Exception('Cannot use native targets until a compiler is configured by setting the native.compilers option')
defineOption('native.compilers', __CompilersNotSpecified())
defineOption('native.libs', [])
defineOption('native.libpaths', [])
defineOption('native.c.flags', None) # defaults to native.cxx.flags if not set
defineOption('native.cxx.flags', [])
defineOption('native.cxx.path', [])
defineOption('native.include', [])
defineOption('native.link.flags', [])

if isWindows():
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
	""" A target that compiles a C++ source file to a .o
	"""
	
	__rebuild_makedepend_count = 0

	def __init__(self, object, source, includes=None, flags=None, dependencies=None, options=None):
		"""
		@param object: the object file to generate
		@param source: a (list of) source files
		
		@param includes: a (list of) include directories, as strings or PathSets, 
		each with a trailing slash. 
		If this target depends on some include files that are generated by another target, 
		make sure it's a directory target since all include directories must either 
		exist before the build starts or be targets themselves. 
		If specifying a subdirectory of a generated directory, use DirGeneratedByTarget. 
		
		@param flags: a list of additional compiler flags
		
		@param dependencies: a list of additional dependencies that need to be built 
		before this target. Usually this is not needed. 
		
		@param options: [DEPRECATED - use .option() instead]
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
		includedirs = self._getIncludeDirs(context)
		for path in includedirs:
			r.append('include dir: '+os.path.normcase(path))
		del path
		
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
		
		# first, figure out if we need to (re-)run makedepends or can use the cached info from the last build
		runmakedepends = False
		
		if targetmtime == 0:
			runmakedepends = True
		
		alreadychecked = set() # paths that we've already checked the date of
		sourcepaths = []
		for path, _ in self.source.resolveWithDestinations(context):
			mtime = getmtime(path)
			alreadychecked.add(path)
			sourcepaths.append(path)
			if mtime > newestTime: newestFile, newestTime = path, mtime
		if newestTime > targetmtime: runmakedepends = True
		
		if (not runmakedepends) and os.path.exists(makedependsfile): # (no point using stat cache for this file)
			# read file from last time; if any of the transitive dependencies 
			# have changed, we should run makedepends again to update them
			with io.open(makedependsfile, 'r', encoding='utf-8') as f:
				flags = f.readline().strip()
				if flags != u'flags: %s'%self._getCompilerFlags(context):
					runmakedepends = True
				else:
					for path in f:
						path = path.strip()
						mtime = getmtime(path)
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
			
			# find the newest time from these files; if this is same as previous makedepends, won't do anything
			for path in makedependsoutput:
				if path in alreadychecked: continue
				mtime = getmtime(path)
				if mtime > newestTime: newestFile, newestTime = path, mtime
			
			# write out new makedepends file for next time
			mkdir(os.path.dirname(makedependsfile))
			with io.open(makedependsfile, 'w', encoding='utf-8') as f:
				f.write(u'flags: %s\n'%self._getCompilerFlags(context))
				for path in makedependsoutput:
					f.write(u'%s\n'%path)

		# endif runmakedepends
		
		# include the newest timestamp as an implicit input, so that we'll rebuild if any include files have changed
		# no need to log this, as targetwrapper already logs differences in implicit inputs
		if newestFile is not None:
			newestDateTime = datetime.datetime.fromtimestamp(newestTime)
			r.append(u'newest dependency was modified at %s.%03d: %s'%(
				newestDateTime.strftime('%a %Y-%m-%d %H:%M:%S'), 
				newestDateTime.microsecond/1000, 
				os.path.normcase(newestFile)))

		if time.time()-startt > 5: # this should usually be pretty quick, so if it takes a while it may indicate a real build file mistake
			self.log.warn('C/C++ dependency generation took a long time: %0.1f s to evaluate %s', time.time()-startt, self)
		
		return r
		
class C(Cpp):
	""" A target that compiles a C source file to a .o
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
	""" A target that links object files to binaries
	"""
	
	def __init__(self, bin, objects, libs=None, libpaths=None, shared=False, options=None, flags=None, dependencies=None):
		"""
		@param bin: the output binary

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
				libs=flatten([map(string.strip, context.expandPropertyValues(x, expandList=True)) for x in self.libs+options['native.libs'] if x]),
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
	""" A target that compiles .a files from collections of .o files
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
		
exename = make_functor(lambda c, i:c.mergeOptions()['native.cxx.exenamefn'](c.expandPropertyValues(i)), name='exename')
objectname = make_functor(lambda c, i:c.mergeOptions()['native.cxx.objnamefn'](c.expandPropertyValues(i)), name='objectname')
libname = make_functor(lambda c, i:c.mergeOptions()['native.cxx.libnamefn'](c.expandPropertyValues(i)), name='libname')
staticlibname = make_functor(lambda c, i:c.mergeOptions()['native.cxx.staticlibnamefn'](c.expandPropertyValues(i)), name='staticlibname')


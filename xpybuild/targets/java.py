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
# $Id: java.py 301527 2017-02-06 15:31:43Z matj $
#

"""
Contains targets for building and documenting Java applications. 

The main target in this module is `xpybuild.targets.java.Jar`.

The directory containing the JDK is identified by the option ``java.home``. 

"""
import os, inspect, os.path, shutil

from xpybuild.buildcommon import *
from xpybuild.basetarget import BaseTarget, targetNameToUniqueId
from xpybuild.propertysupport import defineOption
from xpybuild.pathsets import PathSet, FilteredPathSet, BasePathSet
from xpybuild.utils.fileutils import mkdir, deleteDir, openForWrite, normLongPath
from xpybuild.utils.java import jar, javac, create_manifest, javadoc, signjar
from xpybuild.utils.flatten import flatten
from xpybuild.utils.outputhandler import ProcessOutputHandler
from xpybuild.utils.buildexceptions import BuildException

import logging
import zipfile
import collections

# Options specific to this target
defineOption('jar.manifest.classpathAppend', [])
defineOption('javac.logs', '${BUILD_WORK_DIR}/javac_logs')

def _isJavaFile(p): return p.lower().endswith('.java')

class SignJars(BaseTarget):
	""" Copy jars into a target directory and sign them with the supplied keystore, optionally also updating their manifests. 
	
	Additional command line arguments can be passed to ``signjars`` using the option ``jarsigner.options`` (default ``[]``). 
	
	"""
	def __init__(self, output, jars, keystore, alias=None, storepass=None, manifestDefaults=None):
		""" 
		@param output: The output directory in which to put the signed jars

		@param jars: The list (or PathSet) of input jars to copy and sign

		@param keystore: The path to the keystore

		@param alias: The alias for the keystore (optional)

		@param storepass: The password for the store file (optional)

		@param manifestDefaults: a dictionary of manifest entries to add to the existing manifest.mf file
		of each jar before signing.  Entries in this dictionary will be ignored if the same entry
		is found in the original manifest.mf file already.
		"""
		self.jars = PathSet(jars)
		self.keystore = keystore
		self.alias = alias
		self.storepass = storepass
		self.manifestDefaults = manifestDefaults
		BaseTarget.__init__(self, output, [self.jars, self.keystore])

	def run(self, context):
		self.keystore = context.expandPropertyValues(self.keystore)
		options = self.options

		mkdir(self.path)
		for src, dest in self.jars.resolveWithDestinations(context):
			if '..' in dest:
					# to avoid people abusing this to copy files outside the dest directory!
					raise Exception('This target does not permit destination paths to contain ".." relative path expressions')

			try:
				with open(src, 'rb') as s:
					with openForWrite(os.path.join(self.path, dest), 'wb') as d:
						d.write(s.read())

				shutil.copystat(src, os.path.join(self.path, dest))
				
				# When we re-jar with the user specified manifest entries, jar will complain
				# about duplicate attributes IF the original MANIFEST.MF already has those entries.
				# This is happening for latest version of SL where Application-Name, Permission etc
				# were already there.
				#
				# The block of code below will first extract the original MANIFEST.MF from the source
				# jar file, read all manifest entry to a list.  When constructing the new manifest entries,
				# make sure the old MANIFEST.MF doesn't have that entry before putting the new manifest entry
				# to the list.  This will avoid the duplicate attribute error.
				#  
			
				if self.manifestDefaults:
					
					lines = []
					
					# read each line of MANIFEST.MF of the original jar and put them in lines
					with zipfile.ZipFile(src, 'r') as zf:
						lst = zf.infolist()
						for zi in lst:
							fn = zi.filename
							if fn.lower().endswith('manifest.mf'):
								try:
									manifest_txt = zf.read(zi.filename).decode('utf-8', errors='strict')
								except Exception as e:
									raise BuildException('Failed reading the manifest file %s with exception:%s' % (fn, e))

								# if we have all manifest text, parse and save each line
								if manifest_txt:
									# CR LF | LF | CR  can be there as line feed and hence the code below
									lines = manifest_txt.replace('\r\n', '\n').replace('\r','\n').split('\n')
										
								# done
								break
						
					
					original_entries = collections.OrderedDict()  # to ensure we don't overwrite/duplicate these
					# populate the manifest_entries with original values from original manifest
					for l in lines:
						if ':' in l and not l.startswith(' '): # ignore continuation lines etc because keys are all we care about
							key,value = l.split(':', 1)
							original_entries[key] = value.strip()
					
					# build up a list of the new manifest entries (will be merged into any existing manifest by jar)
					manifest_entries = collections.OrderedDict()
					for i in self.manifestDefaults:
						# if entry isn't there yet, add to the list
						if i not in original_entries:
							manifest_entries[i] = context.expandPropertyValues(self.manifestDefaults[i])
		
					# create the manifest file
					# we want to add the manifest entries explicitly specified here but 
					# NOT the 'default' manifest entries we usually add, since these 
					# are likely to have been set already, and we do not want duplicates
					mkdir(self.workDir)
					manifest = os.path.join(self.workDir, "MANIFEST.MF") # manifest file

					options = dict(options)
					options['jar.manifest.defaults'] = {}
					create_manifest(manifest, manifest_entries, options)
	
					# update the EXISTING jar file with the new manifest entries, which will be merged into 
					# existing manifest by the jar tool
					jar(os.path.join(self.path, dest), manifest, None, options, update=True)
	
				signjar(os.path.join(self.path, dest), self.keystore, options, alias=self.alias, storepass=self.storepass, 
					outputHandler=ProcessOutputHandler.create('signjars', treatStdErrAsErrors=False, options=options))
			except BuildException as e:
				raise BuildException('Error processing %s: %s'%(os.path.basename(dest), e))

class Javac(BaseTarget):
	""" Compile Java classes to a directory (without creating a ``.jar``). 
	
	Example usage::
	
		Jar('${OUTPUT_DIR}/myapp.jar', 
			# FindPaths walks a directory tree, supporting complex ant-style globbing patterns for include/exclude
			compile=[
				FindPaths('./src/', excludes=['**/VersionConstants.java']), 
				'${BUILD_WORK_DIR}/filtered-java-src/VersionConstants.java',
			],
			
			# DirBasedPathSet statically lists dependent paths under a directory
			classpath=[DirBasedPathSet('${MY_DEPENDENT_LIBRARY_DIR}/', 'mydep-api.jar', 'mydep-core.jar')],
			
			# Specify Jar-specific key/values for the MANIFEST.MF (in addition to any set globally via options)
			manifest={'Implementation-Title':'My Amazing Java Application'}, 
			
			package=FindPaths('resources/', includes='**/*.properties'),
		)

		setGlobalOption('jar.manifest.defaults', {'Implementation-Version': '${APP_VERSION}', 'Implementation-Vendor': 'My Company'})

	
	The following options can be set with ``Javac(...).option(key, value)`` 
	or `xpybuild.propertysupport.setGlobalOption()` to customize the compilation process:
		
		- ``javac.warningsAsErrors: bool`` Make the build fail if any warnings are detected. 
		- ``javac.debug = False`` Include debug information (line numbers) in the compiled ``.class`` files. 
		- ``javac.encoding = "ASCII"`` The character encoding for ``.java`` source files. 
		- ``javac.source = ""`` The ``.java`` source compliance level. 
		- ``javac.target = ""`` The ``.class`` compliance level. 
		- ``javac.options = []`` A list of extra options to pass to ``javac``. 
		- ``javac.logs = "${BUILD_WORK_DIR}/javac_logs"`` The directory in which errors/warnings from ``javac`` will be written. 
		- ``javac.outputHandlerFactory = JavacProcessOutputHandler`` The class used to parse and handle error/warning messages. 
	
	"""
	compile = None
	classpath = None
	def __init__(self, output, compile, classpath, options=None):
		""" 
		@param output: output dir for class files

		@param compile: PathSet (or list)  of things to compile

		@param classpath: PathSet (or list) of things to be on the classpath

		@param options: [DEPRECATED - use .option() instead]
		"""
		self.compile = FilteredPathSet(_isJavaFile, PathSet(compile))
			
		self.classpath = PathSet(classpath)
		
		BaseTarget.__init__(self, output, [self.compile,self.classpath])
		if options is not None:
			for k,v in options.items(): self.option(k, v)

	def run(self, context):
		# make sure outputdir exists
		mkdir(self.path)

		# create the classpath, sorting within PathSet (for determinism), but retaining original order of 
		# PathSet elements in the list
		classpath = os.pathsep.join(self.classpath.resolve(context)) 

		# compile everything
		mkdir(self.getOption('javac.logs'))
		javac(self.path, self.compile.resolve(context), classpath, options=self.options, logbasename=self.options['javac.logs']+'/'+targetNameToUniqueId(self.name), targetname=self.name, workDir=self.workDir)

	def getHashableImplicitInputs(self, context):
		# changes in the manifest text should cause a rebuild
		# for now, don't bother factoring global jar.manifest.defaults option 
		# in here (it'll almost never change anyway)
		return super(Javac, self).getHashableImplicitInputs(context) + sorted([
			'option: %s = "%s"'%(k,v) for (k,v) in self.options.items() 
				if v and (k.startswith('javac.') or k == 'java.home')])

class Jar(BaseTarget):
	""" Create a jar, first compiling some Java classes, then packing it all up as a ``.jar``. 
	
	In addition to the options listed on the `Javac` target, the following options can be set when 
	creating a Jar, using ``Jar(...).option(key, value)`` or `xpybuild.propertysupport.setGlobalOption()`:
		
		- ``jar.manifest.defaults = {}`` Default key/value pairs (e.g. version number) to include in the ``MANIFEST.MF`` of every jar. 
		- ``jar.manifest.classpathAppend = []`` Add additional classpath entries to the ``MANIFEST.MF`` which are needed at runtime but not during compilation. 
		- ``jar.options = []`` A list of extra options to pass to ``jar``. 
	"""
	compile = None
	classpath = None
	package = None
	manifest = None
	def __init__(self, jar, compile, classpath, manifest, options=None, package=None, preserveManifestFormatting=False):
		""" 

		@param jar: path to jar to create.

		@param compile: PathSet (or list)  of things to compile.

		@param classpath: PathSet (or list) of things to be on the classpath; 
			destination mapping indicates how they will appear in the manifest.

		@param manifest: Typically a map of ``MANIFEST.MF`` entries (can be empty) such as::
		
				manifest={'Implementation-Title':'My Amazing Java Application'}, 
			
			Alternative, specify a string to get the manifest from a file, or ``None`` 
			to disable manifest generation and just produce a normal zip. 

		@param options: (deprecated - use ``.option()`` instead). 

		@param package: PathSet (or list) of other files to include in the jar; 
			destination mapping indicates where they will appear in the jar.
		
		@param preserveManifestFormatting: an advanced option that prevents the jar tool from 
			reformatting the specified manifest file to comply with Java conventions 
			(also prevents manifest merging if jar already exists).

		
		"""
		self.compile = FilteredPathSet(_isJavaFile, PathSet(compile)) if compile else None
			
		self.classpath = PathSet(classpath)
		
		self.package = PathSet(package)
		self.manifest = manifest
		BaseTarget.__init__(self, jar, [self.compile,self.classpath,self.package, 
			manifest if isinstance(manifest, str) else None])
			
		for k,v in (options or {}).items(): self.option(k, v)
		self.preserveManifestFormatting = preserveManifestFormatting

	def run(self, context):
		options = self.options

		# make sure temp dir exists
		mkdir(self.workDir)

		classes = os.path.join(self.workDir, "classes") # output dir for classes
		
		# create the classpath, sorting within PathSet (for determinism), but retaining original order of 
		# PathSet elements in the list
		classpath = os.pathsep.join(self.classpath.resolve(context)) 

		# compile everything
		mkdir(classes) # (need this for assembling other files to package later on, even if we don't do any javac)
		if self.compile:
			mkdir(self.getOption('javac.logs'))
			javac(classes, self.compile.resolve(context), classpath, options=options, logbasename=options.get('javac.logs')+'/'+targetNameToUniqueId(self.name), targetname=self.name, workDir=self.workDir)

		manifest = os.path.join(self.workDir, "MANIFEST.MF") # manifest file
	
		if isinstance(self.manifest, str):
			manifest = context.getFullPath(self.manifest, self.baseDir)
		elif self.manifest == None:
			manifest = None
		else: # generate one
			# rewrite property values in the manifest
			manifest_entries = {}
			for i in self.manifest:
				manifest_entries[i] = context.expandPropertyValues(self.manifest[i])
	
			# determine classpath for manifest
			classpath_entries = []
			
			if "Class-path" not in manifest_entries: # assuming it wasn't hardcoded, set it here
				for src, dest in self.classpath.resolveWithDestinations(context):
					# we definitely do want to support use of ".." in destinations here, it can be very useful
					classpath_entries.append(dest)
				assert isinstance(options['jar.manifest.classpathAppend'], list), options['jar.manifest.classpathAppend'] # must not be a string
				classpath_entries.extend(options['jar.manifest.classpathAppend'] or [])
				
				# need to always use / not \ for these to be valid
				classpath_entries = [p.replace(os.path.sep, '/').replace('\\', '/') for p in classpath_entries if p]
				
				if classpath_entries:
					manifest_entries["Class-path"] = " ".join(classpath_entries) # include the classpath from here
			if not manifest_entries.get('Class-path'): # suppress this element entirely if not needed, otherwise there would be no way to have an empty classpath
				manifest_entries.pop('Class-path','')
			
			# create the manifest file
			create_manifest(manifest, manifest_entries, options=options)

		# copy in the additional things to include
		for (src, dest) in self.package.resolveWithDestinations(context):
			if '..' in dest: raise Exception('This target does not permit packaged destination paths to contain ".." relative path expressions')
			mkdir(os.path.dirname(os.path.join(classes, dest)))
			destpath = normLongPath(classes+'/'+dest)
			srcpath = normLongPath(src)

			if os.path.isdir(srcpath):
				mkdir(destpath)
			else:
				with open(srcpath, 'rb') as s:
					with openForWrite(destpath, 'wb') as d:
						d.write(s.read())

		# create the jar
		jar(self.path, manifest, classes, options=options, preserveManifestFormatting=self.preserveManifestFormatting, 
			outputHandler=ProcessOutputHandler.create('jar', treatStdErrAsErrors=False,options=options))

	def getHashableImplicitInputs(self, context):
		# changes in the manifest text should cause a rebuild
		# for now, don't bother factoring global jar.manifest.defaults option 
		# in here (it'll almost never change anyway)
		return super(Jar, self).getHashableImplicitInputs(context) + [
			'manifest = '+context.expandPropertyValues(str(self.manifest)),
			'classpath = '+context.expandPropertyValues(str(self.classpath)), # because classpath destinations affect manifest
			]+(['preserveManifestFormatting = true'] if self.preserveManifestFormatting else [])\
			+sorted(['option: %s = "%s"'%(k,v) for (k,v) in self.options.items() 
				if v and (k.startswith('javac.') or k.startswith('jar.') or k == 'java.home')])

class Javadoc(BaseTarget):
	""" Creates Javadoc from a set of input files. 
	
	The following options can be set with ``Javadoc(...).option(key, value)`` to customize the documentation process:
		
		- ``javadoc.title = "Documentation"`` The title. 
		
		- ``javac.ignoreSourceFilesFromClasspath = False`` By default, Javadoc will parse any source .java files 
		  present in the classpath in case they contain comments 
		  that should be inherited by the source files being documented. If these files contain errors (such as missing 
		  optional dependencies) it will cause Javadoc to fail. This option prevents the classpath from being searched 
		  for source files (by setting -sourcepath to a non-existent directoryu), which avoids errors and may also speed 
		  up the Javadoc generation. 

		- ``javac.access = "public"`` Identifies which members and classes to include. 
		
	"""
	def __init__(self, destdir, source, classpath, options):
		"""
		@param destdir: directory to create docs in

		@param source: a set of files to build from

		@param classpath: a list of jars needed for the classpath

		@param options: [DEPRECATED - use .option() instead]
		"""
		self.sources = PathSet(source)
		self.classpath = PathSet(classpath)
		BaseTarget.__init__(self, destdir, [self.sources, self.classpath])
		for k,v in (options or {}).items(): self.option(k, v)

	def run(self, context):
		options = self.options
		classpath = os.pathsep.join(self.classpath.resolve(context))
		javadoc(self.path, self.sources.resolve(context), classpath, options, 
			outputHandler=ProcessOutputHandler.create('javadoc', treatStdErrAsErrors=False, options=options), workDir=self.workDir)

	def getHashableImplicitInputs(self, context):
		# changes in the manifest text should cause a rebuild
		# for now, don't bother factoring global jar.manifest.defaults option 
		# in here (it'll almost never change anyway)
		return super(Javadoc, self).getHashableImplicitInputs(context) + \
			sorted(['option: %s = "%s"'%(k,v) for (k,v) in self.options.items() 
				if k and k.startswith('javadoc.')])
				

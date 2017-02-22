# xpyBuild - eXtensible Python-based Build System
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
# $Id: java.py 301527 2017-02-06 15:31:43Z matj $
#

import os, inspect, os.path, shutil

from buildcommon import *
from basetarget import BaseTarget, targetNameToUniqueId
from propertysupport import defineOption
from pathsets import PathSet, FilteredPathSet, BasePathSet
from utils.fileutils import mkdir, deleteDir, openForWrite, normLongPath
from utils.java import jar, javac, create_manifest, javadoc, signjar, dumpApi
from utils.flatten import flatten
from utils.outputhandler import ProcessOutputHandler
from buildexceptions import BuildException
import logging
import zipfile
import collections

# Options specific to this target
defineOption('jar.manifest.classpathAppend', [])
defineOption('javac.logs', '${BUILD_WORK_DIR}/javac_logs')

def _isJavaFile(p): return p.lower().endswith('.java')

class SignJars(BaseTarget):
	""" Copy jars into a target directory and sign them with the supplied keystore, optionally also updating their manifests
	"""
	def __init__(self, output, jars, keystore, alias=None, storepass=None, manifestDefaults=None):
		""" 
		output -- The output directory in which to put the signed jars

		jars -- The list (or PathSet) of input jars to copy and sign

		keystore -- The path to the keystore

		alias -- The alias for the keystore (optional)

		storepass -- The password for the store file (optional)

		manifestDefaults -- a dictionary of manifest entries to add to the existing manifest.mf file
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
		options = context.mergeOptions(self) # get the merged options

		mkdir(self.path)
		for src, dest in self.jars.resolveWithDestinations(context):
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
									manifest_txt = zf.read(zi.filename)
								except Exception, e:
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

					options['jar.manifest.defaults'] = {}
					create_manifest(manifest, manifest_entries, options)
	
					# update the EXISTING jar file with the new manifest entries, which will be merged into 
					# existing manifest by the jar tool
					jar(os.path.join(self.path, dest), manifest, None, options, update=True)
	
				signjar(os.path.join(self.path, dest), self.keystore, options, alias=self.alias, storepass=self.storepass, 
					outputHandler=ProcessOutputHandler('signjars', treatStdErrAsErrors=False, options=options))
			except BuildException, e:
				raise BuildException('Error processing %s: %s'%(os.path.basename(dest), e))

class Javac(BaseTarget):
	""" Compile java source to a directory (without jarring it)
	"""
	compile = None
	classpath = None
	def __init__(self, output, compile, classpath, options=None):
		""" 
		output -- output dir for class files

		compile -- PathSet (or list)  of things to compile

		classpath -- PathSet (or list) of things to be on the classpath; 

		options -- generic target options map for passing options to the 
			underlying operation (optional)
		"""
		self.compile = FilteredPathSet(_isJavaFile, PathSet(compile))
			
		self.classpath = PathSet(classpath)
		
		BaseTarget.__init__(self, output, [self.compile,self.classpath])
		self.options = options

	def run(self, context):
		options = context.mergeOptions(self) # get the merged options

		# make sure outputdir exists
		mkdir(self.path)

		# create the classpath, sorting within PathSet (for determinism), but retaining original order of 
		# PathSet elements in the list
		classpath = os.pathsep.join(self.classpath.resolve(context)) 

		# compile everything
		mkdir(options.get('javac.logs'))
		javac(self.path, self.compile.resolve(context), classpath, options=options, logbasename=options.get('javac.logs')+'/'+targetNameToUniqueId(self.name), targetname=self.name)

	def getHashableImplicitInputs(self, context):
		# changes in the manifest text should cause a rebuild
		# for now, don't bother factoring global jar.manifest.defaults option 
		# in here (it'll almost never change anyway)
		return super(Javac, self).getHashableImplicitInputs(context) + sorted([
			'option: %s = "%s"'%(k,v) for (k,v) in context.mergeOptions(self).items() 
				if v and (k.startswith('javac.') or k == 'java.home')])

class Jar(BaseTarget):
	""" Create a Jar, first compiling some java, then packing it all up
	"""
	compile = None
	classpath = None
	package = None
	manifest = None
	apiChange = False
	def __init__(self, jar, compile, classpath, manifest, options=None, package=None, preserveManifestFormatting=False):
		""" 
		jar -- path to jar to create

		compile -- PathSet (or list)  of things to compile

		classpath -- PathSet (or list) of things to be on the classpath; 
			destination mapping indicates how they will appear in the manifest

		manifest -- map of manifest entries, OR a string with the filename to use 
			OR None to disable manifest generation and just produce a normal zip

		options -- generic target options map

		package -- PathSet (or list) of other files to include in the jar; 
			destination mapping indicates where they will appear in the kar
		"""
		self.compile = FilteredPathSet(_isJavaFile, PathSet(compile)) if compile else None
			
		self.classpath = PathSet(classpath)
		
		self.package = PathSet(package)
		self.manifest = manifest
		BaseTarget.__init__(self, jar, [self.compile,self.classpath,self.package, 
			manifest if isinstance(manifest, basestring) else None])
			
		self.options = options
		self.preserveManifestFormatting = preserveManifestFormatting

	def run(self, context):
		options = context.mergeOptions(self) # get the merged options

		# make sure temp dir exists
		mkdir(self.workDir)

		classes = os.path.join(self.workDir, "classes") # output dir for classes
		
		# create the classpath, sorting within PathSet (for determinism), but retaining original order of 
		# PathSet elements in the list
		classpath = os.pathsep.join(self.classpath.resolve(context)) 

		# compile everything
		mkdir(classes) # (need this for assembling other files to package later on, even if we don't do any javac)
		if self.compile:
			mkdir(options.get('javac.logs'))
			javac(classes, self.compile.resolve(context), classpath, options=options, logbasename=options.get('javac.logs')+'/'+targetNameToUniqueId(self.name), targetname=self.name)

		manifest = os.path.join(self.workDir, "MANIFEST.MF") # manifest file
	
		if isinstance(self.manifest, basestring):
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
					classpath_entries.append(dest)
				assert isinstance(options['jar.manifest.classpathAppend'], list) # must not be a string
				classpath_entries.extend(options['jar.manifest.classpathAppend'] or [])
				if classpath_entries:
					manifest_entries["Class-path"] = " ".join(classpath_entries) # include the classpath from here
			if not manifest_entries.get('Class-path'): # suppress this element entirely if not needed, otherwise there would be no way to have an empty classpath
				manifest_entries.pop('Class-path','')
	
			# create the manifest file
			create_manifest(manifest, manifest_entries, options=options)

		# copy in the additional things to include
		for (src, dest) in self.package.resolveWithDestinations(context):
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
		newapi = dumpApi(classes, options=options)
		newapi = [l.strip() for l in newapi]
		apifile = self.workDir+"_api.txt"
		if os.path.exists(apifile):
			oldapi = []
			with open(apifile) as f:
				oldapi = [l.strip() for l in f]
			self.apiChange = newapi != oldapi				
		else:
			self.apiChange = True

		if self.apiChange:
			with openForWrite(apifile, "wb") as f:
				f.writelines([x+os.linesep for x in newapi])
		
		jar(self.path, manifest, classes, options=options, preserveManifestFormatting=self.preserveManifestFormatting, 
			outputHandler=ProcessOutputHandler('jar', treatStdErrAsErrors=False,options=options))

	def getHashableImplicitInputs(self, context):
		# changes in the manifest text should cause a rebuild
		# for now, don't bother factoring global jar.manifest.defaults option 
		# in here (it'll almost never change anyway)
		return super(Jar, self).getHashableImplicitInputs(context) + [
			'manifest = '+context.expandPropertyValues(str(self.manifest)),
			'classpath = '+context.expandPropertyValues(str(self.classpath)), # because classpath destinations affect manifest
			]+sorted(['option: %s = "%s"'%(k,v) for (k,v) in context.mergeOptions(self).items() 
				if v and (k.startswith('javac.') or k.startswith('jar.') or k == 'java.home')])

	def _activateDependency(self, dep):
		return not isinstance(dep, Jar) or self.apiChange
	def _getStampFile(self, dep):
		return self.path if not isinstance(dep, Jar) else self.workDir+"_api.txt"


class Javadoc(BaseTarget):
	""" Creates javadoc from a set of input files
	"""
	def __init__(self, destdir, source, classpath, options):
		"""
			destdir -- directory to create docs in

			source -- a set of files to build from

			classpath -- a list of jars needed for the classpath

			options -- javadoc.-prefixed options map
		"""
		self.sources = PathSet(source)
		self.classpath = PathSet(classpath)
		BaseTarget.__init__(self, destdir, [self.sources, self.classpath])
		self.options = options

	def run(self, context):
		options = context.mergeOptions(self) # get the merged options
		classpath = os.pathsep.join(self.classpath.resolve(context))
		javadoc(self.path, self.sources.resolve(context), classpath, options, 
			outputHandler=ProcessOutputHandler('javadoc', treatStdErrAsErrors=False, options=options))

	def getHashableImplicitInputs(self, context):
		# changes in the manifest text should cause a rebuild
		# for now, don't bother factoring global jar.manifest.defaults option 
		# in here (it'll almost never change anyway)
		return super(Javadoc, self).getHashableImplicitInputs(context) + \
			sorted(['option: %s = "%s"'%(k,v) for (k,v) in context.mergeOptions(self).items() 
				if k and k.startswith('javadoc.')])
				

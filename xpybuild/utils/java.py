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


"""
Support classes for the Java targets in `xpybuild.targets.java`. 
"""

import os, sys, re, subprocess
import locale

from xpybuild.buildcommon import *
from xpybuild.propertysupport import defineOption
from xpybuild.utils.process import call
from xpybuild.utils.outputhandler import ProcessOutputHandler
from xpybuild.utils.flatten import getStringList
from xpybuild.utils.fileutils import deleteDir, mkdir, deleteFile, openForWrite, normLongPath
from xpybuild.utils.consoleformatter import publishArtifact

from xpybuild.utils.buildexceptions import BuildException

import logging
log = logging.getLogger('utils.java')

# General java options
defineOption('java.home', None)

# Options for creating manifests
defineOption('jar.manifest.defaults', {})

def create_manifest(path, properties, options):
	""" Create a manifest file in path from the map properties.

	@param path: The absolute path in which to create a manifest file. If None is specified, 
	no file is written but a byte string containing the file contents is returned. 

	@param properties: A map of manifest keys to values (unicode character strings). 
	Must follow java jar file format specification, e.g. headers cannot contain spaces. 

	@param options: The options to use for creating the manifest (prefix: jar.manifest)

	"""
	# merge in the defaults to the map (properties will already have been expanded
	fullmap = {}
	for source in [options['jar.manifest.defaults'], properties]:
		for key in source:
			fullmap[key] = source[key]
	

	# build up the list of lines
	lines = []
	for key in sorted(fullmap.keys()): # select a deterministic order
		# strip whitespace since it isn't needed, and could confuse the continuation character logic
		line = ("%s: %s") % (key.strip(), fullmap[key].strip())
		assert ' ' not in key.strip(), 'manifest.mf key "%s" does not confirm to jar file specification - cannot contain spaces'%(key.strip())
		assert '\n' not in line, repr(line)
		
		# assume character strings as input; must convert to utf8 before applying continuation char logic
		line = line.encode('utf-8')
		
		# spec says: No line may be longer than 72 bytes (not characters), in its UTF8-encoded form
		# If a value would make the initial line longer than this, it should be continued on extra lines (each starting with a single SPACE).
		maxbytes = 72-1 # remove one byte for the newline
		while len(line) > maxbytes:
			lines.append(line[:maxbytes])
			line = b" %s" % line[maxbytes:]
		assert line
		lines.append(line)
	lines.append(b'') # need a trailing newline else Java ignores last line!

	lines = b'\n'.join(lines) # don't use os.linesep for simplicity, and because spec says only \r\n, \n, \r are valid not \n\r

	# write out the file
	if path:
		with openForWrite(path, 'wb') as f:
			f.write(lines)
	else: # this case for unit testing
		return lines

# Options for javac
defineOption('javac.options', [])
defineOption('javac.source', "") # e.g. 1.6
defineOption('javac.target', "")
defineOption('javac.encoding', "ASCII") # best to set this explicitly else its OS dependent
defineOption('javac.debug', False)
defineOption('javac.warningsAsErrors', False)

class JavacProcessOutputHandler(ProcessOutputHandler):
	def __init__(self, targetName, **kwargs): # unusually, we pass in the targetname here, since there are usually so many different "javac"s
		ProcessOutputHandler.__init__(self, 'javac', **kwargs)
		self._current = None
		self._chunks = []
		self._logbasename = None
		self._contents = ''
		self._targetName = targetName
	
	def setJavacLogBasename(self, path):
		self._logbasename = path
		return self
	
	def handleLine(self, l, isstderr=True):
		if not isstderr: return # ignore stdout messages, we only care about warnings and errors
		if l.strip().startswith('Note:'): return # annoying and pointless messages
		self._contents += l+'\n'
		
		l = l.rstrip()
		if re.match('\d+ (errors|warnings)',l): return
		if l.startswith('error: warnings found'): return
		if l.startswith('Picked up _JAVA_OPTIONS'): return
		
		# support for ProcessOutputHandler.Options.regexIgnore
		if self._regexIgnore is not None and self._regexIgnore.match(l): return
			
		# assume everything else is an error or a warning
			
		#if self._current and l.strip() == '^': # this is the last line of a chunk (jdk 1.6, but doesn't work with 1.7)
		#	self._current.append(l)
		#	self._current = None
		if not self._current or (re.match('.*\.java:\d+: .*', l) or l.startswith('error:') or l.startswith('warning:')): # this is the first line of a chunk
			self._current = [l]
			self._chunks.append(self._current)
		else:
			self._current.append(l)
	
	def handleEnd(self, returnCode=None):
		assert self._logbasename # could make this optional, but for now don't
		
		if self._contents:
			with openForWrite(self._logbasename+'.out', 'w', encoding='utf-8') as fo:
				fo.write(self._contents)
		
		errs = []
		warns = []
		errmsg = None
		for c in self._chunks:
			loc = re.match('(.*\.java:\d+): *(.*)', c[0])
			msg = re.match('.*\.java:\d+: *(.*)', c[0])
			if msg and loc: 
				msg, loc = msg.group(1), loc.group(1) # key by message
			else:
				msg = c[0]
				loc = None
			# special-case merging for common multi-line messages to give better diagnostics
			i = 1
			while i < len(c):
				if c[i].strip().startswith('symbol'):
					msg += ': <'+re.search('symbol *: *(.*)', c[i]).group(1)+'>'
					del c[i]
				elif c[i].strip().startswith('location'):
					msg += ' in <'+re.search('location *: *(.*)', c[i]).group(1)+'>'
					del c[i]
				else: 
					i += 1
				
			# check returncode since we must never treat stderr output as an error if it returned success, as annotation processes can output all kinds of stuff
			iswarning = returnCode==0 or (re.match('.*\.java:\d+: warning: .*', c[0]) or (len(c) > 1 and 'to suppress this warning' in c[1]))
			addto = warns if iswarning else errs
			existing = next((x[1] for x in addto if x[0] == msg), None)
			if not existing:
				existing = []
				addto.append( (msg, existing) )
			existing.append([loc+': '+msg if loc else msg]+c[1:])
			if not iswarning and not errmsg: errmsg = msg+(' at %s'%loc if loc else '')
	
		if errs:
			with openForWrite(self._logbasename+'-errors.txt', 'w', encoding='utf-8') as fo:
				for x in errs:
					# x[0] is the common msg type, x[1] is a list of places where it occured, each of which 
					
					# in log, summarize the first error of this type (e.g. if a symbol wasn't found in 20 places just log it once)
					filename = None
					lineno = None
					try:
						filename = re.sub("^(.*):([0-9]+): .*",r"\1",x[1][0][0])
						lineno = int(re.sub("^(.*):([0-9]+): .*",r"\2",x[1][0][0]))
					except:
						pass
					self._log(logging.ERROR, '\njavac> '.join(x[1][0]), 
						filename,lineno) 
					
					print('- '+x[0], file=fo)
					print(file=fo)
					i = 0
					for x2 in x[1]: # print the detail of later similar ones only at INFO
						if i != 0:
							self._log(logging.INFO, 'similar error: \n    %s'%('\n    '.join(x2)))
						i+=1
						
						self._errors.append(' / '.join(x2[0]))
						for x3 in x2:
							fo.write(x3)
							print(file=fo)
					print(file=fo)
			self._log(logging.ERROR, '%d javac ERRORS in %s - see %s'%(sum([len(x[1]) for x in errs]), self._targetName, self._logbasename+'-errors.txt'), 
				self._logbasename+'-errors.txt')
			publishArtifact('javac %s errors'%self._targetName, self._logbasename+'-errors.txt')
			
		if warns:
			self._log(logging.WARNING, '%d javac WARNINGS in %s - see %s; first is: %s'%(sum([len(x[1]) for x in warns]), self._targetName, self._logbasename+'-warnings.txt', warns[0][0]), 
				self._logbasename+'-warnings.txt')
			with openForWrite(self._logbasename+'-warnings.txt', 'w', encoding='utf-8') as fo:
				for x in warns:
					if not errmsg and (returnCode != 0): 
						errmsg = x[1][0][0]
						if len(warns)>1:
							errmsg = 'Failed due to %d warnings, first is: %s'%(len(warns), errmsg)
						# it IS worth publishing warnings if they caused a failure
						publishArtifact('javac %s warnings'%self._targetName, self._logbasename+'-warnings.txt')
					print('- '+x[0], file=fo)
					print(file=fo)
					for x2 in x[1]:
						for x3 in x2:
							print(x3, file=fo)
			# might add an option to publish warnings as artifacts, but don't by default as it happens a lot on some projects
			#_publishArtifact(self._logbasename+'-warnings.txt')
		
		if errmsg: 
			msg = errmsg
			if len(self._errors)>1:
				msg = '%d errors, first is: %s'%(len(self._errors), errmsg)
		elif returnCode:
			msg = 'javac failed with return code %s'%(returnCode)
		else:
			assert not errs
			return
		
		publishArtifact('javac %s output'%self._targetName, self._logbasename+'.out')
		
		raise BuildException(msg)


def javac(output, inputs, classpath, options, logbasename, targetname, workDir):
	""" Compile some java files to class files.

	Will raise BuildException if compilation fails.

	@param output: path to a directory in which to put the class files (will be created)

	@param inputs: list of paths (.java files) to be compiled

	@param classpath: classpath to compile with, as a string

	@param options: options map. javac.options is a list of additional arguments, javac.source is the source version, 
	javac.target is the target version

	@param logbasename: absolute, expanded, path to a directory and filename prefix 
		to use for files such as .err, .out, etc files

	@param targetname: to log appropriate error messages
	
	@param workDir: where temporary files are stored.  

	"""

	assert logbasename and '$' not in logbasename
	logbasename = os.path.normpath(logbasename)
	# make the output directory
	if not os.path.exists(output): mkdir(output)
	# location of javac
	if options['java.home']:
		javacpath = os.path.join(options['java.home'], "bin/javac")
	else:
		javacpath = "javac" # just get it from the path
	# store the list of files in a temporary file, then build from that.
	mkdir(workDir)
	
	argsfile = os.path.join(workDir, "javac_args.txt")
	
	# build up the arguments
	args = ["-d", output]
	if options["javac.source"]: args.extend(["-source", options["javac.source"]])
	if options["javac.target"]: args.extend(["-target", options["javac.target"]])
	if options["javac.encoding"]: args.extend(["-encoding", options["javac.encoding"]])
	if options["javac.debug"]:
		args.append('-g')
	if options['javac.warningsAsErrors']:
		args.append('-Werror')
	# TODO: should add -Xlint options here I think
		
	args.extend(getStringList(options['javac.options']))
	if classpath: args.extend(['-cp', classpath])
	args.extend([x for x in inputs if x.endswith('.java')]) # automatically filter out non-java files

	with openForWrite(argsfile, 'w', encoding=locale.getpreferredencoding()) as f:
		for a in args:
			f.write('"%s"'%a.replace('\\','\\\\')+'\n')

	success=False
	try:

		log.info('Executing javac for %s, writing output to %s: %s', targetname, logbasename+'.out', ''.join(['\n\t"%s"'%x for x in [javacpath]+args]))
		
		# make sure we have no old ones hanging around still
		try:
			deleteFile(logbasename+'-errors.txt', allowRetry=True)
			deleteFile(logbasename+'-warnings.txt', allowRetry=True)
			deleteFile(logbasename+'.out', allowRetry=True)
		except Exception as e:
			log.info('Cleaning up file failed: %s' % e)
		
		outputHandler = options.get('javac.outputHandlerFactory', JavacProcessOutputHandler)(targetname, options=options)
		if hasattr(outputHandler, 'setJavacLogBasename'):
			outputHandler.setJavacLogBasename(logbasename)
		call([javacpath, "@%s" % argsfile], outputHandler=outputHandler, outputEncoding='UTF-8', cwd=output, timeout=options['process.timeout'])
		if (not os.listdir(output)): # unlikely, but useful failsafe
			raise EnvironmentError('javac command failed to create any target files (but returned no error code); see output at "%s"'%(logbasename+'.out'))
		success = True
	finally:
		if not success and classpath:
			log.info('Classpath for failed javac was: \n   %s', '\n   '.join(classpath.split(os.pathsep)))


defineOption('jar.options', [])
defineOption('javac.outputHandlerFactory', JavacProcessOutputHandler)

def jar(path, manifest, sourcedir, options, preserveManifestFormatting=False, update=False, outputHandler=None):
	""" Create a jar file containing a manifest and some other files

	@param path: jar file to create. Typically this file does not already exist, but if it does 
	then the specified files or manifest will be merged into it. 
	
	@param manifest: path to the manifest.mf file (or None to disable manifest entirely)

	@param sourcedir: the directory to pack everything from (this method may add extra files to this dir)

	@param options: options map. jar.options is a list of additional arguments

	@param preserveManifestFormatting: an advanced option that prevents that jar executable from 
	reformatting the specified manifest file to comply with Java conventions 
	(also prevents manifest merging if jar already exists)
	"""
	# work out if we need to create a parent directory
	dir = os.path.dirname(path)
	if dir and not os.path.exists(dir): mkdir(dir)
	# location of jar
	if options['java.home']:
		binary = os.path.join(options['java.home'], "bin/jar")
	else:
		binary = "jar"
	# build up arguments
	args = [binary]
	args.extend(options['jar.options'])

	if update:
		mode='-u'
	else:
		mode='-c'
	
	if not manifest: 
		args.extend([mode+"fM", path])
	elif preserveManifestFormatting:
		mkdir(sourcedir+'/META-INF')
		srcf = normLongPath(sourcedir+'/META-INF/manifest.mf')

		with open(manifest, 'rb') as s:
			with openForWrite(srcf, 'wb') as d:
				d.write(s.read())
		args.extend([mode+"f", path])
	else:
		args.extend([mode+"fm", path, manifest])

	if sourcedir: 
		args.extend(["-C", sourcedir, "."])


	# actually call jar
	call(args, outputHandler=outputHandler, timeout=options['process.timeout'])
	
defineOption('jarsigner.options', [])

def signjar(path, keystore, options, alias=None, storepass=None, outputHandler=None):
	""" Signs an existing jar.

	@param path: Jar file to sign

	@param keystore: The keystore with which to sign it

	@param options: The current set of options to be used

	@param alias: An alias for the key (optional)

	@param storepass: The password for the keystore (optional)

	@param outputHandler: the output handler (optional)
	"""
	if options['java.home']:
		binary = os.path.join(options['java.home'], "bin/jarsigner")
	else:
		binary = "jarsigner"

	args = [binary]
	args.extend(options['jarsigner.options'])
	args.extend(['-keystore', keystore])
	if storepass: args.extend(['-storepass', storepass])
	args.append(path)
	if alias: args.append(alias)

	call(args, outputHandler=outputHandler, timeout=options['process.timeout'])

defineOption('javadoc.options', [])
defineOption('javadoc.title', "Documentation")
defineOption('javadoc.access', "public")
""" By default, Javadoc will parse any source .java files present in the classpath in case they contain comments 
that should be inherited by the source files being documented. If these files contain errors (such as missing 
optional dependencies) it will cause Javadoc to fail. This option prevents the classpath from being searched 
for source files (by setting -sourcepath to a non-existent directoryu), which avoids errors and may also speed 
up the Javadoc generation. 
"""
defineOption('javadoc.ignoreSourceFilesFromClasspath', False)

def javadoc(path, sources, classpath, options, workDir, outputHandler):
	""" Create javadoc from sources and a set of options

	@param path: The directory under which to create the javadoc

	@param sources: a list of source files

	@param classpath: a list of jars for the classpath

	@param options: the current set of options to use
	
	@param workDir: where temporary files are stored
	
	@param outputHandler: the output handler (optional)
	"""
	deleteDir(path)
	mkdir(path)
	# location of javadoc
	if options['java.home']:
		binary = os.path.join(options['java.home'], "bin/javadoc")
	else:
		binary = "javadoc"

	# store the list of files in a temporary file, then build from that.
	mkdir(workDir)
	inputlistfile = os.path.join(workDir, "javadoc.inputs")
	with openForWrite(inputlistfile, 'w', encoding=locale.getpreferredencoding()) as f:
		f.writelines('"'+x.replace('\\','\\\\')+'"'+'\n' for x in sources)

	# build up arguments
	args = [binary]
	args.extend(options['javadoc.options'])
	if options['javadoc.ignoreSourceFilesFromClasspath']:
		args.extend(['-sourcepath', path+'/xpybuild_fake_sourcepath'])
	args.extend([
		"-d", path,
		"-classpath", classpath,
		"-windowtitle", options['javadoc.title'],
		"-doctitle", options['javadoc.title'],
		"-%s" % options['javadoc.access'],
		"@%s" % inputlistfile
	])
	# actually call javadoc
	call(args, outputHandler=outputHandler, timeout=options['process.timeout'])


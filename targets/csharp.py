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
# $Id: csharp.py 301527 2017-02-06 15:31:43Z matj $
#

import os, inspect

from buildcommon import *
from basetarget import BaseTarget
from propertysupport import defineOption
from utils.process import call
from pathsets import PathSet, FilteredPathSet
from buildcontext import getBuildInitializationContext
from buildexceptions import BuildException
from utils.outputhandler import ProcessOutputHandler
from utils.fileutils import mkdir

import logging, re

defineOption('csharp.compiler', "")
defineOption('csharp.options', [])

class CSCProcessOutputHandler(ProcessOutputHandler):
	"""
	A ProcessOutputHandler than can parse the output of the CSC compiler
	"""

	def _parseLocationFromLine(self, line):
		m = re.match("(.*)[(](\d+)(,\d+)?[)]: (.*)", line) # allow line,col
		if m:
			return m.group(1),m.group(2),m.group(3)[1:] if m.group(3) else None, m.group(4)+' - '+m.group(1)
		else:
			return None,None,None,line

# functor or constructor taking a process name and returning a new 
# ProcessOutputHandler with handleLine and handleEnd methods. 
defineOption('csharp.processoutputhandler', CSCProcessOutputHandler) 

def _isDotNetFile(p): return p.lower().endswith('.cs')

class CSharp(BaseTarget):
	""" Compile C# files to an executable or dll
	"""
	compile = None
	main = None
	libs = None
	def __init__(self, output, compile, main=None, libs=None, flags=None, dependencies=None, resources=None):
		""" 
		@param output: the resulting .exe or .dll
		
		@param compile: the input PathSet, path or list of .cs file(s)
		
		@param main: The main class to execute if an exe is to be built.
		If this is set then an executable will be created.
		Otherwise this target will build a library.

		@param libs: a list of input libraries (or a PathSet)
		"""
		self.compile = FilteredPathSet(_isDotNetFile, PathSet(compile))
		self.main = main
		self.flags = flags or []
		self.libs = PathSet(libs or [])
		self.resources = resources or []
		BaseTarget.__init__(self, output, [self.compile, self.libs, [x for (x, y) in self.resources], dependencies or []])
		self.tags('c#')

	def getHashableImplicitInputs(self, context):
		return super(CSharp, self).getHashableImplicitInputs(context) + (['main = %s'%context.expandPropertyValues(('%s'%self.main))] if self.main else [])

	def run(self, context):
		options = context.mergeOptions(self) # get the merged options
		libs = self.libs.resolve(context)
		libnames = map(lambda x:os.path.basename(x), libs)
		libpaths = map(lambda x:os.path.dirname(x), libs)
		flags = [context.expandPropertyValues(x) for x in self.flags]

		args = [options['csharp.compiler'], "-out:"+self.path]
		if libnames: args.extend(["-reference:"+",".join(libnames), "-lib:"+",".join(libpaths)])
		if self.main:
			args.extend(["-target:exe", "-main:"+self.main])
		else:
			args.append("-target:library")
		for (file, id) in self.resources:
			args.append('-resource:%s,%s' % (context.expandPropertyValues(file), context.expandPropertyValues(id)))
		args.extend(options['csharp.options'])
		args.extend(flags)
		args.extend(self.compile.resolve(context))

		mkdir(os.path.dirname(self.path))
		call(args, outputHandler=options['csharp.processoutputhandler']('csc', False, options=options), timeout=options['process.timeout'])

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

"""
Contains `xpybuild.targets.csharp.CSharp` for  compiling C# files to an executable or library. 
"""

import os, inspect

from xpybuild.buildcommon import *
from xpybuild.basetarget import BaseTarget
from xpybuild.propertysupport import defineOption
from xpybuild.utils.process import call
from xpybuild.pathsets import PathSet, FilteredPathSet
from xpybuild.buildcontext import getBuildInitializationContext
from xpybuild.utils.buildexceptions import BuildException
from xpybuild.utils.outputhandler import ProcessOutputHandler
from xpybuild.utils.fileutils import mkdir

import logging, re

defineOption('csharp.compiler', "")
defineOption('csharp.options', [])

class CSCProcessOutputHandler(ProcessOutputHandler):
	"""
	A ProcessOutputHandler that can parse the output of the CSC compiler.
	"""

	def _parseLocationFromLine(self, line):
		m = re.match("(.*)[(](\d+)(,\d+)?[)]: (.*)", line) # allow line,col
		if m:
			return m.group(1),m.group(2),m.group(3)[1:] if m.group(3) else None, m.group(4)+' - '+m.group(1)
		else:
			return None,None,None,line

# functor or constructor taking a process name and returning a new 
# ProcessOutputHandler with handleLine and handleEnd methods. 
defineOption('csharp.outputHandlerFactory', CSCProcessOutputHandler) 

def _isDotNetFile(p): return p.lower().endswith('.cs')

class CSharp(BaseTarget):
	""" Compile C# files to produce an executable or library file. 
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
		libs = self.libs.resolve(context)
		libnames = [os.path.basename(x) for x in libs]
		libpaths = [os.path.dirname(x) for x in libs]
		flags = [context.expandPropertyValues(x) for x in self.flags]

		args = [self.getOption('csharp.compiler'), "-out:"+self.path]
		if libnames: args.extend(["-reference:"+",".join(libnames), "-lib:"+",".join(libpaths)])
		if self.main:
			args.extend(["-target:exe", "-main:"+self.main])
		else:
			args.append("-target:library")
		for (file, id) in self.resources:
			args.append('-resource:%s,%s' % (context.expandPropertyValues(file), context.expandPropertyValues(id)))
		args.extend(self.options['csharp.options'])
		args.extend(flags)
		args.extend(self.compile.resolve(context))

		mkdir(os.path.dirname(self.path))
		call(args, outputHandler=self.getOption('csharp.outputHandlerFactory')('csc', False, options=self.options), timeout=self.options['process.timeout'])

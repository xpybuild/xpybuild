# xpyBuild - eXtensible Python-based Build System
#
# Late-binding functors for use in property-expansion and modification
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
# $Id: propertyfunctors.py 301527 2017-02-06 15:31:43Z matj $
#

import os, re

from xpybuild.utils.functors import Composable, ComposableWrapper

from xpybuild.buildcontext import BaseContext
from xpybuild.pathsets import PathSet, BasePathSet

class dirname(Composable):
	""" A late-binding function which performs property expansion on its argument and then
	    removes the file parts of the argument.
	"""
	def __init__(self, path):
		""" 
		@param path: The input path, possibly containing unreplaced properties.
		"""
		# the input path may be composable
		self.arg = path
		
	def resolveToString(self, context):
		""" Perform the expansion and dirname on the argument path.

		@param context: a BuildContext

		>>> str(dirname("path/"))
		'dirname()'
		>>> str(dirname("path/${foo}/bar"))
		'dirname(path/${foo})'
		>>> str(dirname("path/${foo}/bar/"))
		'dirname(path/${foo})'
		>>> dirname("${PATH}").resolveToString(BaseContext({'PATH':'/path/base'})).replace(os.sep,'/')
		'/path'
		>>> dirname("${PATH}").resolveToString(BaseContext({'PATH':'/path/base/'})).replace(os.sep,'/')
		'/path'
		>>> str("${OUTPUT_DIR}/"+dirname("${INPUT}"))
		'${OUTPUT_DIR}/+dirname(${INPUT})'
		>>> ("${OUTPUT_DIR}"+dirname("${INPUT}")).resolveToString(BaseContext({'OUTPUT_DIR':'/target', 'INPUT':'/libs/foo'})).replace(os.sep,'/')
		'${OUTPUT_DIR}/libs'
		>>> str(dirname("${A}"+dirname("${B}")))
		'dirname(${A}+dirname(${B}))'
		>>> dirname("${A}"+dirname("${B}")).resolveToString(BaseContext({'A':'/foo/bar-', 'B':'/baz/quux'})).replace(os.sep,'/')
		'/foo/bar-'
		"""
		return os.path.dirname(context.getFullPath(self.arg, "${OUTPUT_DIR}").rstrip(os.path.sep))
	
	def __str__(self):
		arg = ('%s'%self.arg).replace(os.path.sep,'/').rstrip('/')
		
		# might as well run dirname on it before generating __str__, it 
		# isn't expanded yet but this at least makes it as short as possible -
		# though only if it's a string, if it's a Composable this wouldn't be 
		# appropriate
		if isinstance(self.arg, str) and '/' in self.arg:
			arg = os.path.dirname(arg)
		
		return "dirname("+arg+")"


class basename(Composable):
	""" A late-binding function which performs property expansion on its argument and then
	    removes the directory parts of the argument.
	"""
	def __init__(self, path):
		""" 
		@param path: The input path, possibly containing unreplaced properties.
		"""
		# the input path may be composable
		self.arg = path
		
	def resolveToString(self, context):
		""" Perform the expansion and basename on the argument path.

		@param context: a BuildContext

		>>> str(basename("path/"))
		'basename(path)'
		>>> str(basename("path/${foo}/bar"))
		'basename(bar)'
		>>> str(basename("path/${foo}/bar/"))
		'basename(bar)'
		>>> basename("${PATH}").resolveToString(BaseContext({'PATH':'/path/base'}))
		'base'
		>>> basename("${PATH}").resolveToString(BaseContext({'PATH':'/path/base/'}))
		'base'
		>>> str("${OUTPUT_DIR}/"+basename("${INPUT}"))
		'${OUTPUT_DIR}/+basename(${INPUT})'
		>>> ("${OUTPUT_DIR}/"+basename("${INPUT}")).resolveToString(BaseContext({'OUTPUT_DIR':'/target', 'INPUT':'/libs/foo'}))
		'${OUTPUT_DIR}/foo'
		>>> str(basename("${A}"+basename("${B}")))
		'basename(${A}+basename(${B}))'
		>>> basename("${A}"+basename("${B}")).resolveToString(BaseContext({'A':'/foo/bar-', 'B':'/baz/quux'}))
		'bar-quux'
		"""
		return os.path.basename(context.getFullPath(self.arg, "${OUTPUT_DIR}").rstrip(os.path.sep))
	
	def __str__(self):
		arg = ('%s'%self.arg).replace(os.path.sep,'/').rstrip('/')
		
		# might as well run basename on it before generating __str__, it 
		# isn't expanded yet but this at least makes it as short as possible -
		# though only if it's a string, if it's a Composable this wouldn't be 
		# appropriate
		if isinstance(self.arg, str):
			arg = os.path.basename(arg)
		
		return "basename("+arg+")"

class sub(Composable):
	""" A late-binding function which performs regex substitution.
	    The pattern is passed through verbatim, the replacement and the input
	    have property expansion performed on them before invoking the regular
	    expression.

	    The pattern/replacement syntax is the same as re.sub
	"""
	def __init__(self, pat, rep, arg):
		"""
		@param pat: the regex pattern to match

		@param rep: the replacement string

		@param arg: the input
		"""
		self.pat = pat
		self.rep = rep
		self.arg = arg
	def resolveToString(self, context):
		""" Do property expansion on the inputs and then perform the regex 
	
		@param context: a BuildContext

		>>> str(sub('a','b','aa'))
		'sub(a,b,aa)'
		>>> sub('a','b','aa').resolveToString(BaseContext({}))
		'bb'
		>>> str("output/"+sub('a', '${REP}', '${INPUT}'))
		'output/+sub(a,${REP},${INPUT})'
		>>> ("output/"+sub('a', '${REP}', '${INPUT}')).resolveToString(BaseContext({'REP':'c', 'INPUT':'aa'}))
		'output/cc'
		>>> str("output/"+sub('b', sub('c','d','${REP}'), sub('a','b','${INPUT}')))
		'output/+sub(b,sub(c,d,${REP}),sub(a,b,${INPUT}))'
		>>> ("output/"+sub('b', sub('c','d','${REP}'), sub('a','b','${INPUT}'))).resolveToString(BaseContext({'REP':'c', 'INPUT':'aa'}))
		'output/dd'
		"""
		return re.sub(self.pat, context.expandPropertyValues(self.rep), context.expandPropertyValues(self.arg))
	def __str__(self):
		return "sub(%s,%s,%s)"%(self.pat, self.rep, self.arg)

class joinPaths(Composable):
	""" A late-binding function which resolves the specified PathSet and 
		then joins its contents together to form a string using os.pathsep or a 
		specified separator character. 
	"""
	def __init__(self, pathset, pathsep=os.pathsep):
		self.pathset = pathset if isinstance(pathset, BasePathSet) else PathSet(pathset)
		self.pathsep = pathsep
	def resolveToString(self, context):
		""" Do property expansion on the inputs and then perform the regex 
	
		@param context: a BuildContext
		"""
		return self.pathsep.join(self.pathset.resolve(context))
	def __str__(self):
		return "joinPaths(%s with %s)"%(self.pathset, self.pathsep)

def make_functor(fn, name=None):
	""" Take an arbitrary function and return a functor that cna take arbitrary 
	arguments and that can in turn be curried into
	a composable object for use in property contexts.

	Example::

		def fn(context, input):
			... # do something
			return input

		myfn = make_functor(fn)

		target = "${OUTPUT_DIR}/" + myfn("${MYVAR}")

	This will execute fn(context, "${MYVAR}") at property expansion time and then
	prepend the expanded "${OUTPUT_DIR}/".

	@param fn: a function of the form fn(context, *args)

	>>> str(make_functor(lambda context, x: context.expandPropertyValues(x))('${INPUT}'))
	'<lambda>(${INPUT})'
	
	>>> str(make_functor(lambda context, x: context.expandPropertyValues(x), name='foobar')('${INPUT}'))
	'foobar(${INPUT})'
	
	>>> make_functor(lambda context, x: context.expandPropertyValues(x))('${INPUT}').resolveToString(BaseContext({'INPUT':'foo'}))
	'foo'
	
	>>> str("output/"+make_functor(lambda context, x: context.expandPropertyValues(x))('${INPUT}'))
	'output/+<lambda>(${INPUT})'
	
	>>> ("output/"+make_functor(lambda context, x: context.expandPropertyValues(x))('${INPUT}')).resolveToString(BaseContext({'INPUT':'foo'}))
	'output/foo'
	"""
	return ComposableWrapper(fn, name)



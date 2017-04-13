# xpyBuild - eXtensible Python-based Build System
#
# Late-binding functors for use in property-expansion and modification (internal support classes)
#
# Copyright (c) 2014 - 2017 Software AG, Darmstadt, Germany and/or its licensors
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
# $Id: functors.py 301527 2017-02-06 15:31:43Z matj $
#

class Composable(object):
	""" Base class for objects which are late-bound and can be composed 
		 together and with strings, with a resolveToString method to 
		 produce the output string.
	"""
	def resolveToString(self, context):
		raise Exception('Must implement resolveToString')
	def __add__(self, other):
		""" Compose this with another object (string or a Composable) """
		return Compose(self, other)
	def __radd__(self, other):
		""" Compose this with another object (string or a Composable) """
		return Compose(other, self)
	def __str__(self):
		""" A unique representation of the composable """
		return "unknown_composable()"
	def __repr__(self):
		""" A unique representation of the composable """
		return str(self)

class Compose(Composable):
	""" A functor that composes other functors or strings """
	def __init__(self, left, right):
		"""
		@param left: The left object to compose
		@param right: The right object to compose
		"""
		self.left = left
		self.right = right
	def resolveToString(self, context):
		""" Compose the two objects. Strings as literals, other objects are invoked with context argument.

		@param context: a BuildContext

		>>> Compose('a', 'b').resolveToString(None)
		'ab'
		>>> Compose(Compose('a', 'b'), 'c').resolveToString(None)
		'abc'
		>>> Compose('a', Compose('b', 'c')).resolveToString(None)
		'abc'
		>>> Compose(Compose('a', 'b'), Compose('c', 'd')).resolveToString(None)
		'abcd'
		>>> str("a"+Compose('b', 'c'))
		'a+b+c'
		>>> ("a"+Compose('b', 'c')).resolveToString(None)
		'abc'
		>>> str(Compose('a', 'b')+"c")
		'a+b+c'
		>>> (Compose('a', 'b')+"c").resolveToString(None)
		'abc'
		"""
		left = self.left if isinstance(self.left, basestring) else self.left.resolveToString(context)
		right = self.right if isinstance(self.right, basestring) else self.right.resolveToString(context)
		return left + right
	def __str__(self):
		return str(self.left)+"+"+str(self.right)

class ComposableFn(Composable):
	""" A functor wrapping an arbitrary function and arguments that can be composed """
	def __init__(self, fn, *args, **kwargs):
		"""
		@param fn: The function to wrap. Must have the format fn(context, *args)
		@param args: Arguments to the function
		@keyword name: optional display name for the functor
		"""
		self.fn = fn
		self.args = args
		self.name=kwargs.get('name',None) or self.fn.__name__ # use <lambda> if not specified
		# any other kwargs are currently ignored
	def resolveToString(self, context):
		""" Execute the function with the context and arguments as arguments,

		@param context: a BuildContext

		>>> ComposableFn(lambda context, a, b: a+b, 'a', 'b').resolveToString(None)
		'ab'
		>>> str("a"+ComposableFn(lambda context, x: x, 'b'))
		'a+<lambda>(b)'
		>>> ("a"+ComposableFn(lambda context, x: x, 'b')).resolveToString(None)
		'ab'
		"""
		return self.fn(context, *self.args)
	def __str__(self):
		return self.name+"("+",".join(map(str, self.args))+")"

class ComposableWrapper:
	""" A functor which wraps a function and can be curried into a ComposableFunction """
	def __init__(self, fn, name=None):
		""" 
		@param fn: a function of the form fn(context, *args)
		"""
		self.fn = fn
		self.name=name
	def __call__(self, *args, **kwargs):
		""" Currys fn with *args into a ComposableFn which can be used in compositions and later evaluated """
		return ComposableFn(self.fn, *args, name=self.name)


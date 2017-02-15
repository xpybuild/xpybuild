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
# $Id: touch.py 301527 2017-02-06 15:31:43Z matj $
#

import os, inspect, markdown

from propertysupport import *
from pathsets import *
from buildcommon import *
from basetarget import BaseTarget
from utils.fileutils import openForWrite, normLongPath, mkdir

defineOption('markdown.extensions', [])
defineOption('markdown.encoding', 'utf-8')
defineOption('markdown.tab_length', 4)
defineOption('markdown.output_format', 'html4')
defineOption('markdown.extension_configs', {})

class Markdown(BaseTarget):
	""" A target that converts markdown into HTML
	"""
	
	def __init__(self, target, source, options=None):
		"""
		name -- the output filename
		"""
		source = PathSet(source)
		BaseTarget.__init__(self, target, [source])
		self.src = source
		self.options = options
	
	def run(self, context):

		src = self.src.resolveWithDestinations(context)
		if not isDirPath(self.name):
			if 1 != len(src):
				raise BuildException('Markdown destination must be a directory (ending with "/") when multiple sources are specified (not: %s)' % self.name)
			src, mappedDest = src[0]
			self.callMarkdown(context, self.path, src)
		else:
			for src, mappedDest in src:
				self.callMarkdown(context, self.path+mappedDest, src)

	def callMarkdown(self, context, dest, src):
		mkdir(os.path.dirname(dest))

		options = context.mergeOptions(self)
		dest = os.path.splitext(dest)[0]+'.html'
		dest = normLongPath(dest)
		src = normLongPath(src)

		markdown.markdownFromFile(input=src, output=dest, encoding=options['markdown.encoding'], output_format=options['markdown.output_format'], extension_configs=options['markdown.extension_configs'], extensions=options['markdown.extensions'], tab_length=options['markdown.tab_length'])


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

import os, inspect

from buildcommon import *
from propertysupport import *
from basetarget import BaseTarget
from pathsets import PathSet
from utils.fileutils import openForWrite, normLongPath, mkdir
from utils.process import call
from buildexceptions import BuildException
from utils.outputhandler import ProcessOutputHandler

defineOption('docker.path', 'docker')
defineOption('docker.host', None)
defineOption('docker.processoutputhandler', ProcessOutputHandler) 

class Docker(BaseTarget):
	""" A target that runs commands in docker, using stamp files for up-to-dateness
	"""
	BUILD = 1
	PUSHTAG = 2
	
	def __init__(self, imagename, mode, inputs, depimage=None, dockerfile=None, buildArgs=None):
		"""
		imagename: the name/tag of the image to build
		"""
		self.imagename = imagename
		self.depimage = depimage
		self.mode = mode
		self.dockerfile = dockerfile
		self.buildArgs = buildArgs
		self.stampfile = '${BUILD_WORK_DIR}/targets/docker/.%s' % re.sub(r'[\\/]', '_', imagename)
		self.depstampfile = '${BUILD_WORK_DIR}/targets/docker/.%s' % re.sub(r'[\\/]', '_', depimage) if depimage else None
		self.inputs = PathSet(inputs)
		BaseTarget.__init__(self, self.stampfile, inputs + ([self.depstampfile] if self.depstampfile else []))

	def clean(self, context):
		BaseTarget.clean(self, context)
		args = [ options['docker.path'] ]
		environs = { 'DOCKER_HOST' : self.options['docker.host'] } if self.options['docker.host'] else {}
		args.extend(['rmi', context.expandPropertyValues(self.imagename)])
		call(args, outputHandler=self.getOption('docker.processoutputhandler')('docker-rmi', False, options=self.options), timeout=self.options['process.timeout'], env=environs)
	
	def run(self, context):
		options = self.options
		args = [ self.getOption('docker.path') ]
		environs = { 'DOCKER_HOST' : options['docker.host'] } if options['docker.host'] else {}
		if self.mode == Docker.BUILD:
			dargs = list(args)
			dargs.extend([
					'build', '--rm=true', '-t', context.expandPropertyValues(self.imagename),
				])
			if self.buildArgs: dargs.extend(["--build-arg=%s" % [context.expandPropertyValues(x) for x in self.buildArgs]])
			if self.dockerfile: dargs.extend(["-f", context.expandPropertyValues(self.dockerfile)])
			inputs = self.inputs.resolve(context)
			if len(inputs) != 1: raise BuildException("Must specify a single input for Docker.BUILD", location = self.location)
			dargs.append(inputs[0])
			cwd = os.path.dirname(inputs[0])
			call(dargs, outputHandler=options['docker.processoutputhandler']('docker-build', False, options=options), timeout=options['process.timeout'], env=environs, cwd=cwd)
		elif self.mode == Docker.PUSHTAG:
			inputs = self.inputs.resolve(context)
			if len(inputs) != 0: raise BuildException("Must not specify inputs for Docker.PUSHTAG", location = self.location)
			dargs = list(args)
			dargs.extend([
					'tag', context.expandPropertyValues(self.depimage), context.expandPropertyValues(self.imagename),
				])
			call(dargs, outputHandler=options['docker.processoutputhandler']('docker-tag', False, options=options), timeout=options['process.timeout'], env=environs)
			dargs = list(args)
			dargs.extend([
					'push', context.expandPropertyValues(self.imagename),
				])
			call(dargs, outputHandler=options['docker.processoutputhandler']('docker-push', False, options=options), timeout=options['process.timeout'], env=environs)
		else:
			raise BuildException('Unknown Docker mode. Must be Docker.BUILD or Docker.PUSHTAG', location = self.location)
		
		# update the stamp file
		path = normLongPath(self.path)
		mkdir(os.path.dirname(path))
		with openForWrite(path, 'wb') as f:
			pass



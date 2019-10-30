# xpyBuild - eXtensible Python-based Build System
#
# Copyright (c) 2013 - 2018 Software AG, Darmstadt, Germany and/or its licensors
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
defineOption('docker.buildoptions', [])
defineOption('docker.outputHandlerFactory', ProcessOutputHandler) 

class DockerBase(BaseTarget):
	""" A target that runs commands in docker, using stamp files for up-to-dateness
	"""
	
	def __init__(self, imagename, inputs, depimage=None, dockerfile=None, buildArgs=None, dockerArgs=None):
		"""
		imagename: the name/tag of the image to build
		"""
		self.imagename = imagename
		self.depimage = depimage
		self.dockerfile = dockerfile
		self.buildArgs = buildArgs
		self.dockerArgs = dockerArgs
		self.stampfile = '${BUILD_WORK_DIR}/targets/docker/.%s' % re.sub(r'[\\/]', '_', imagename)
		self.depstampfile = '${BUILD_WORK_DIR}/targets/docker/.%s' % re.sub(r'[\\/]', '_', depimage) if depimage else None
		self.inputs = PathSet(inputs)
		BaseTarget.__init__(self, self.stampfile, inputs + ([self.depstampfile] if self.depstampfile else []))

	def clean(self, context):
		BaseTarget.clean(self, context)
		args = [ self.getOption('docker.path') ]
		environs = { 'DOCKER_HOST' : self.getOption('docker.host') } if self.getOption('docker.host') else {}
		args.extend(['rmi', context.expandPropertyValues(self.imagename)])
		try:
			call(args, outputHandler=self.getOption('docker.outputHandlerFactory')('docker-rmi', treatStdErrAsErrors=False, options=self.options), timeout=self.getOption('process.timeout'), env=environs)
		except Exception as e:
			logger = logging.getLogger('DockerBase')
			logger.info('Exception cleaning Docker target: %s' % e)
	
	def run(self, context):
		args = [ self.getOption('docker.path') ]
		environs = { 'DOCKER_HOST' : self.getOption('docker.host') } if self.getOption('docker.host') else {}

class DockerBuild(DockerBase):
	def __init__(self, imagename, inputs, depimage=None, dockerfile=None, buildArgs=None, dockerArgs=None):
		DockerBase.__init__(self, imagename, inputs, depimage, dockerfile, buildArgs, dockerArgs)

	def run(self, context):
		args = [ self.getOption('docker.path') ]
		environs = { 'DOCKER_HOST' : self.getOption('docker.host') } if self.getOption('docker.host') else {}

		dargs = list(args)
		dargs.extend([
				'build', '--rm=true', '-t', context.expandPropertyValues(self.imagename),
			])
		dargs.extend(self.getOption('docker.buildoptions'))
		if self.dockerArgs: dargs.extend(self.dockerArgs)
		if self.buildArgs: dargs.extend(["--build-arg=%s" % context.expandPropertyValues(x) for x in self.buildArgs])
		if self.dockerfile: dargs.extend(["-f", context.expandPropertyValues(self.dockerfile)])
		inputs = self.inputs.resolve(context)
		if len(inputs) != 1: raise BuildException("Must specify a single input for Docker.BUILD", location = self.location)
		dargs.append(inputs[0])
		cwd = os.path.dirname(inputs[0])
		call(dargs, outputHandler=self.getOption('docker.outputHandlerFactory')('docker-build', treatStdErrAsErrors=False, options=self.options), timeout=self.getOption('process.timeout'), env=environs, cwd=cwd)
	
		# update the stamp file
		self.updateStampFile()

class DockerPushTag(DockerBase):
	def __init__(self, imagename, fromimage):
		DockerBase.__init__(self, imagename, [], depimage=fromimage)

	def run(self, context):
		args = [ self.getOption('docker.path') ]
		environs = { 'DOCKER_HOST' : self.getOption('docker.host') } if self.getOption('docker.host') else {}

		inputs = self.inputs.resolve(context)
		if len(inputs) != 0: raise BuildException("Must not specify inputs for Docker.PUSHTAG", location = self.location)
		dargs = list(args)
		dargs.extend([
				'tag', context.expandPropertyValues(self.depimage), context.expandPropertyValues(self.imagename),
			])
		call(dargs, outputHandler=self.getOption('docker.outputHandlerFactory')('docker-tag', treatStdErrAsErrors=False, options=self.options), timeout=self.getOption('process.timeout'), env=environs)
		dargs = list(args)
		dargs.extend([
				'push', context.expandPropertyValues(self.imagename),
			])
		call(dargs, outputHandler=self.getOption('docker.outputHandlerFactory')('docker-push', treatStdErrAsErrors=False, options=self.options), timeout=self.getOption('process.timeout'), env=environs)
		
		# update the stamp file
		self.updateStampFile()



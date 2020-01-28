# Targets for interacting with FTP sites
#
# $Copyright (c) 2015, 2017-2018, 2020 Software AG, Darmstadt, Germany and/or Software AG USA Inc., Reston, VA, USA, and/or its subsidiaries and/or its affiliates and/or their licensors.$
# Use, reproduction, transfer, publication or disclosure is prohibited except as specifically provided for in your License Agreement with Software AG
#
# $Id: ftp.py 318763 2017-10-20 09:56:15Z matj $

"""
Contains `xpybuild.targets.download.Download` for downloading a file from an FTP or HTTP server. 
"""

import os, urllib.request, urllib.parse, urllib.error

from xpybuild.basetarget import *
from xpybuild.buildcommon import *
from xpybuild.utils.buildexceptions import *
from xpybuild.utils.fileutils import mkdir

class Download(BaseTarget):
	""" Target for downloading from FTP or HTTP.
	"""
	def __init__(self, output, uri, timeout=60*10):
		"""
		"""
		if isDirPath(output): raise BuildException("Download only supports getting files")
		BaseTarget.__init__(self, output, [])
		self.uri = uri
		self.registerImplicitInput(lambda context: ['URL: %s'%context.expandPropertyValues(uri)])
	def run(self, context):
		mkdir(os.path.dirname(self.path))
		uri = context.expandPropertyValues(self.uri)
		urllib.request.urlretrieve(uri, self.path)


import os, glob, logging
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *
from xpybuild.utils.compilers import GCC, VisualStudio

log = logging.getLogger('xpybuild.tests.native_config')

# some basic defaults for recent default compilers for running our testcases with
if IS_WINDOWS:
	VSROOT=r'c:\Program Files (x86)\Microsoft Visual Studio *'
	if glob.glob(VSROOT):
		VSROOT = sorted(glob.glob(VSROOT))[-1] # pick the latest one
	else:
		raise Exception('Cannot find Visual Studio installed in: %s'%VSROOT)
	
	setGlobalOption('native.include', [
		VSROOT+r"\VC\ATLMFC\INCLUDE", 
		VSROOT+r"\VC\INCLUDE", 
		r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.10240.0\ucrt",
	])
	if not os.path.exists(r"C:\Program Files (x86)\Windows Kits\10"):
		log.warning('WARN - Cannot find expected Windows Kits, got: %s'%sorted(glob.glob(r"C:\Program Files (x86)\Windows Kits\*")))
	if not os.path.exists(r"C:\Program Files (x86)\Windows Kits\10\Lib\10.0.10240.0\ucrtx"):
		log.warning('WARN - Cannot find expected Windows Kits UCRT, got: %s'%sorted(glob.glob(r"C:\Program Files (x86)\Windows Kits\10\Lib\*\*")))
	setGlobalOption('native.libpaths', [
		VSROOT+r"\VC\ATLMFC\LIB\amd64", 
		VSROOT+r"\VC\LIB\amd64", 
		r"C:\Program Files (x86)\Windows Kits\10\Lib\10.0.10240.0\ucrt\x64", 
		r"C:\Program Files (x86)\Windows Kits\10\Lib\10.0.19041.0\um\x64",
	])
	setGlobalOption('native.cxx.path', [
		VSROOT+r"\Common7\IDE",
		VSROOT+r"\VC\BIN\amd64", 
		VSROOT+r"\Common7\Tools", 
		r"c:\Windows\Microsoft.NET\Framework\v3.5",
	])
		
	setGlobalOption('native.compilers', VisualStudio(VSROOT+r'\VC\bin\amd64'))
	setGlobalOption('native.cxx.flags', ['/EHa', '/GR', '/O2', '/Ox', '/Ot', '/MD', '/nologo'])
	
else:
	setGlobalOption('native.compilers', GCC())
	setGlobalOption('native.cxx.flags', ['-fPIC', '-O3', '--std=c++0x'])

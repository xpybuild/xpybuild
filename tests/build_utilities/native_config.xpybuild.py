import os, glob, logging, shutil
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *
from xpybuild.utils.compilers import GCC, VisualStudio

log = logging.getLogger('xpybuild.tests.native_config')

# some basic defaults for recent default compilers for running our testcases with
if IS_WINDOWS:
	__vspatterns=[r'c:\Program Files (x86)\Microsoft Visual Studio 1*', r'C:\Program Files\Microsoft Visual Studio\*\Enterprise']
	__vsfound = sorted(glob.glob(__vspatterns[0]))+sorted(glob.glob(__vspatterns[1]))
	log.critical('Found these VS installations: %s', __vsfound)
	log.critical('msbuild is here on PATH: %s', shutil.which('msbuild.exe'))
	
	if __vsfound:
		VSROOT = __vsfound[-1] # pick the latest one
	else:
		raise Exception('Cannot find Visual Studio installed in: %s'%__vspatterns)
	
	setGlobalOption('native.include', [
		VSROOT+r"\VC\ATLMFC\INCLUDE", 
		VSROOT+r"\VC\INCLUDE", 
		r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.10240.0\ucrt",
	])
	if not os.path.exists(r"C:\Program Files (x86)\Windows Kits\10"):
		log.warning('WARN - Cannot find expected Windows Kits, got: %s'%sorted(glob.glob(r"C:\Program Files (x86)\Windows Kits\*")))
	if not os.path.exists(r"C:\Program Files (x86)\Windows Kits\10\Lib\10.0.10240.0\ucrt"):
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
	
	# If we wanted to support VS 2022 we'd need to update this path
	setGlobalOption('native.compilers', VisualStudio(VSROOT+r'\VC\bin\amd64'))
	setGlobalOption('native.cxx.flags', ['/EHa', '/GR', '/O2', '/Ox', '/Ot', '/MD', '/nologo'])
	
else:
	setGlobalOption('native.compilers', GCC())
	setGlobalOption('native.cxx.flags', ['-fPIC', '-O3', '--std=c++0x'])

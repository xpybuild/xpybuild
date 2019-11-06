import os
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *
from xpybuild.utils.compilers import GCC, VisualStudio

# some basic defaults for recent default compilers for running our testcases with
if IS_WINDOWS:
	VSROOT=r'c:\Program Files (x86)\Microsoft Visual Studio 14.0'
	assert os.path.exists(VSROOT), 'Cannot find Visual Studio installed in: %s'%VSROOT
	setGlobalOption('native.include', [r"%s\VC\ATLMFC\INCLUDE" % VSROOT, r"%s\VC\INCLUDE" % VSROOT, r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.10240.0\ucrt"])
	setGlobalOption('native.libpaths', [r"%s\VC\ATLMFC\LIB\amd64" % VSROOT, r"%s\VC\LIB\amd64" % VSROOT, r"C:\Program Files (x86)\Windows Kits\10\Lib\10.0.10240.0\ucrt\x64", r"C:\Program Files (x86)\Windows Kits\8.1\Lib\winv6.3\um\x64"])
	setGlobalOption('native.compilers', VisualStudio(VSROOT+r'\VC\bin\amd64'))
	setGlobalOption('native.cxx.flags', ['/EHa', '/GR', '/O2', '/Ox', '/Ot', '/MD', '/nologo'])
	setGlobalOption('native.cxx.path', ["%s\Common7\IDE" % VSROOT,r"%s\VC\BIN\amd64" % VSROOT, "%s\Common7\Tools" % VSROOT, r"c:\Windows\Microsoft.NET\Framework\v3.5"])
	
else:
	setGlobalOption('native.compilers', GCC())
	setGlobalOption('native.cxx.flags', ['-fPIC', '-O3', '--std=c++0x'])

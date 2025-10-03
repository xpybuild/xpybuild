import os, glob, logging, shutil
from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *
from xpybuild.utils.compilers import GCC, VisualStudio

log = logging.getLogger('xpybuild.tests.native_config')

# some basic defaults for recent default compilers for running our testcases with
if IS_WINDOWS:
	# A more standard approach would be to execute vswhere.exe (from its well-known location) the vars env script, 
	# and then extract what we need from the output. Or we could get PySys to pass these values through from the environment, 
	# but then we're not testing xpybuild so thoroughly. 
	__vspatterns=[r'c:\Program Files (x86)\Microsoft Visual Studio 1*', r'C:\Program Files\Microsoft Visual Studio\*\Enterprise']
	__vsfound = sorted(glob.glob(__vspatterns[0]))+sorted(glob.glob(__vspatterns[1]))
	log.critical('Found these VS installations: %s', __vsfound)
	log.critical('msbuild is here on PATH: %s', shutil.which('msbuild.exe'))
	
	if __vsfound:
		VSROOT = __vsfound[-1] # pick the latest one
	else:
		raise Exception('Cannot find Visual Studio installed in: %s'%__vspatterns)
	
	def findLatest(pattern):
		results = sorted(glob.glob(pattern))
		if results: return results[-1]
		log.warning('Cannot find any path matching: %s', pattern)
		return pattern.replace('*', '[missing]')

	msvcDir = findLatest(VSROOT+r'\VC\Tools\MSVC\*')
	if not os.path.exists(msvcDir) and os.path.exists(VSROOT+r'\VC\INCLUDE'):
		msvcDir = VSROOT+r'\VC' # fallback for older VS versions like 2019
	ucrtIncludeDir = os.path.dirname(findLatest(r"C:\Program Files (x86)\Windows Kits\10\Include\*\ucrt"))

	setGlobalOption('native.include', [
		msvcDir+r"\ATLMFC\INCLUDE", 
		msvcDir+r"\INCLUDE", 
		ucrtIncludeDir+r"\ucrt",
		ucrtIncludeDir+r"\shared",
		ucrtIncludeDir+r"\um",
		ucrtIncludeDir+r"\winrt",
		ucrtIncludeDir+r"\cppwinrt"
	])


	if not os.path.exists(r"C:\Program Files (x86)\Windows Kits\10"):
		log.warning('WARN - Cannot find expected Windows Kits, got: %s'%sorted(glob.glob(r"C:\Program Files (x86)\Windows Kits\*")))
	#if not os.path.exists(r"C:\Program Files (x86)\Windows Kits\10\Lib\10.0.10240.0\ucrt"):
	#	log.warning('WARN - Cannot find expected Windows Kits UCRT, got: %s'%sorted(glob.glob(r"C:\Program Files (x86)\Windows Kits\10\Lib\*\*")))
	setGlobalOption('native.libpaths', [
		msvcDir+r"\lib\amd64", # modern
		msvcDir+r"\ATLMFC\lib\amd64", # just guessing
		VSROOT+r"\VC\ATLMFC\LIB\amd64", # old
		VSROOT+r"\VC\LIB\amd64", 
		findLatest(r"C:\Program Files (x86)\Windows Kits\10\Lib\*\ucrt\x64"),
		findLatest(r"C:\Program Files (x86)\Windows Kits\10\Lib\*\um\x64"),
	])

	setGlobalOption('native.cxx.path', [
		VSROOT+r"\Common7\IDE",
		VSROOT+r"\VC\BIN\amd64", 
		VSROOT+r"\Common7\Tools", 
		findLatest(r"c:\Windows\Microsoft.NET\Framework\v*"), # was 3.5
	])
	
	toolsBin = msvcDir+r'\bin\amd64' # used for old VS versions like 2019
	if not os.path.exists(toolsBin+'\\cl.exe'):
		toolsBin = msvcDir+r'\bin\Hostx64\x64'
	setGlobalOption('native.compilers', VisualStudio(toolsBin))
	setGlobalOption('native.cxx.flags', ['/EHa', '/GR', '/O2', '/Ox', '/Ot', '/MD', '/nologo'])
	
else:
	setGlobalOption('native.compilers', GCC())
	setGlobalOption('native.cxx.flags', ['-fPIC', '-O3', '--std=c++0x'])

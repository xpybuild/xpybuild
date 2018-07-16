# fileutils - helper methods related to the file system
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
# $Id: fileutils.py 301527 2017-02-06 15:31:43Z matj $
#

import shutil, os, os.path, time, platform, threading
import stat, sys
from utils.flatten import getStringList
import subprocess, errno

import logging
log = logging.getLogger('fileutils')

__isWindows = platform.system()=='Windows'

if __isWindows: # ugly ugly hacks due to stupid windows filesystem semantics. See http://bugs.python.org/issue4944
	try:
		import win32file
		class openForWrite:
			def __init__(self, dest, mode):
				assert mode == 'wb' # the Win32 API only has binary mode, not text mode, so only accept opening in this mode. This also means you must deal with any line ending issues yourself when using this.
				self.dest = dest
			def __enter__(self):
				self.Fd = win32file.CreateFile(self.dest, win32file.GENERIC_WRITE, 
					win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE  | win32file.FILE_SHARE_DELETE, 
					None, win32file.CREATE_ALWAYS, win32file.FILE_ATTRIBUTE_NORMAL, None)
				return self
			def write(self, string):
				win32file.WriteFile(self.Fd, string)
			def writelines(self, lines):
				for l in lines:
					self.write(l)
			def close(self):
				win32file.CloseHandle(self.Fd)
			def __exit__(self, ex_type, ex_val, tb):
				self.close()
	except:
		openForWrite = open
else:
	openForWrite = open


def mkdir(newdir):
	""" Recursively create the specified directory if it doesn't already exist. 
	
	If it does, exit without error. 

	@param newdir: The path to create.
	"""
	newdir=normLongPath(newdir)
	if os.path.isdir(newdir): # already exists
		return
		
	if os.path.isfile(newdir):
		raise IOError("A file with the same name as the desired dir, '%s', already exists" % newdir)
	
	#when multiple threads/processes are creating directories  
	#at the same time, it can be a race
	try:
		os.makedirs(newdir)
	except Exception, e:
		if os.path.isdir(newdir):
			pass
		else:
			raise IOError('Problem creating directory %s: %s' % (newdir, e))

def deleteDir(path, allowRetry=True):
	""" Recursively delete the contents of a directory. 
	
	Contains magic hacks so it works even on paths that exceed the Windows MAX_PATH 260 character length. 

	@param path: the path to delete.

	@param allowRetry: set to False to disable automatic retry of the deletion after a few seconds (in case the error was 
	transient)
	
	"""

	def handleRemoveReadonly(func, path, exc):
		# once we've got this working reliably, might reduce the level of some of these log statements
		excvalue = exc[1]
		log.info("handleRemoveReadonly: error removing path %s (%s %s), will try harder; exists=%s" % (path,errno.errorcode.get(excvalue.errno, "EUNKNOWN"), func, os.path.exists(path)))
		
		if func in (os.rmdir, os.remove):
			
			if not os.path.exists(path): # no idea why this happens, but on windows it does
				log.info("handleRemoveReadonly: suppressing spurious remove exception for already-deleted path: %s", path)
				return

			if excvalue.errno == errno.EACCES: # access denied, make it writable first
				try:
					os.chmod(path, stat.S_IRWXU| stat.S_IRWXG| stat.S_IRWXO) # 0777
					func(path)
					log.info("handleRemoveReadonly: fixed by chmod: %s", path)
					return
				except Exception:
					log.exception('handleRemoveReadonly error while trying to handle EACCES: ')
					if not os.path.exists(path): 
						log.info('handleRemoveReadonly gone now') # surely this never happens? if it does, change the code below
					raise
					
			elif excvalue.errno == errno.ENOTEMPTY: # directory not empty, try again
				try:
					log.info("handleRemoveReadonly: ENOTEMPTY dir - has contents: %s", os.listdir(path))
				except Exception, e:
					log.info("handleRemoveReadonly: ENOTEMPTY dir, could not get contents: %s"%e)
					
				if allowRetry: # avoid danger of infinite recursion if things are going really wrong
					deleteDir(path, allowRetry=False)
					log.info("handleRemoveReadonly: fixed by retrying rmtree for ENOTEMPTY: %s", path)
					return
			elif excvalue.errno == errno.ENOENT: # maybe windows went mad and deleted it anyway
				log.error("handleRemoveReadonly: ENOTENT error was raised by path that still exists: %s"%path)
				raise 
				
		# if we didn't manage to handle this, rethrow
		log.warning("handleRemoveReadonly: still failed to remove path %s (%s %s); exists=%s" % (path,errno.errorcode.get(excvalue.errno, "EUNKNOWN"), func, os.path.exists(path)))
		raise


	path = normLongPath(path)
	if not os.path.exists(path): 
		return

	try:	
		shutil.rmtree(path, ignore_errors=False, onerror=handleRemoveReadonly)
		
	except OSError, e:
		if os.path.isfile(path):
			raise OSError, "Unable to delete dir %s as this is a file not a directory" % (path)
			
		if allowRetry:
			log.warn("Failed to delete dir %s (%s), will retry in 10 seconds" %(path, e))

			# todo: remove these debug comments in time
			#handleslog = os.path.normpath('openhandles_%s.txt'%os.path.basename(path))
			#with open(handleslog, 'w') as f:
			#	handlecmd = [os.path.normpath('c:/dev/apama-lib2/win/all/sysinternals/handle.exe'), '-u', 'c:\\dev\\5.2.0.x\\apama-src', '/accepteula']
			#	#print 'running: ', ' '.join(handlecmd)
			#	subprocess.call(args=handlecmd, stdout=f)
					
			# maybe it was a transient error, so try again a little later
			time.sleep(10.0)
			
			# on windows, try again using a separate process, just in case that 
			# helps to avoid problems with virus checkers, etc
			if __isWindows:
				rmdirresult = os.system(u'rmdir /s /q "%s" 2>1 > /dev/nul'%path)
				log.info("Directory deletion retry using rmdir returned code %d: %s", rmdirresult, path)
				
				# continue to run deleteDir regardless of result, to check it's 
				# really gone, and to give better error messages if we still 
				# can't delete for any reason
				
			deleteDir(path, allowRetry=False)
			log.info("Deleted successfully on retry: %s", path)
		else:
			if os.path.exists(path): 
				# maybe logging this is overkill, consider removing in future
				log.exception("Unable to delete dir %s - original exception is: " % (path))
				raise OSError, "Unable to delete dir %s: %s" % (path, e)

def deleteFile(path, allowRetry=True):
	"""Delete the specified file, with the option of automatically retrying a few times if the first attempt fails 
	(to get around Windows weirdness), throwing an exception if the file still exists at the end of retrying. 
	
	Use this instead of os.remove for improved robustness. 
	
	Does nothing if the file doesn't already exist. 
	
	Contains magic hacks so it works even on paths that exceed the Windows MAX_PATH 260 character length. 

	@param path: The path to delete.

	@param allowRetry: If true, wait for a bit and retry the removal if it fails (default: true)
	
	"""
	path = normLongPath(path)
	try:
		if not os.path.lexists(path): return # use lexists in case we're deleting a symlink
			
		try:
			os.remove(path)
		except Exception:
			if os.path.lexists(path): 
				raise
		
	except OSError, e:
		if os.path.isdir(path):
			raise OSError, "Unable to delete file %s as this is a directory not a file" % (path)
		
		if allowRetry:
			log.debug("Failed to delete file %s on first attempt (%s), will retry in 5 seconds", path, e)
			# maybe it was a transient error, so try again a little later
			# on contended windows machines a 5 second sleep isn't always sufficient to prevent error 32
			time.sleep(10.0)
			deleteFile(path, allowRetry=False)
			log.debug("Deleted file successfully on retry: %s", path)
		else:
			if os.path.lexists(path): 
				if os.path.basename(path) in ('%s'%e):
					raise
				else:
					raise OSError("Unable to delete file %s: %s" % (path, e))

def parsePropertiesFile(lines, excludeLines=None):
	""" 
	Parse the contents of the specified properties file or line list, and return an ordered list 
	of (key,value,lineno) pairs.
	
	@param lines: an open file handle or a sequence that can be iterated over to get each line in the file.

	@param excludeLines: a string of list of strings to search for, any KEY containing these strings will be ignored
	
	>>> parsePropertiesFile(['a','b=c',' z  =  x', 'a=d #foo', '#g=h'])
	[('b', 'c', 2), ('z', 'x', 3), ('a', 'd', 4)]
	>>> parsePropertiesFile(['a=b','c=d#foo','XfooX=e', 'f=h'], excludeLines='foo')
	[('a', 'b', 1), ('c', 'd', 2), ('f', 'h', 4)]
	>>> parsePropertiesFile(['a=b','c=d#foo','XfooX=e', 'f=h'], excludeLines=['foo','h'])
	[('a', 'b', 1), ('c', 'd', 2), ('f', 'h', 4)]
	"""
	excludeLines = getStringList(excludeLines)
	result = []
	
	lineNo = 0
	
	for line in lines:
		lineNo += 1
		
		if '#' in line:
			line = line[:line.find('#')].strip()
		line = line.strip()
		if not line or line.startswith('#') or line.startswith('//') or not '=' in line:
			continue

		key = line[:line.find('=')].strip()
		value = line[line.find('=')+1:].strip()

		if filter(lambda x: x in key, excludeLines):
			log.debug('Ignoring property line due to exclusion: %s', line)
			continue
		
		# NB: we don't have a full implementation of .properties escaping yet (e.g. \n but not \\n etc)
		# but this is all we need for now
		value = value.replace('\\\\','\\')
		
		result.append((key,value, lineNo))
	return result

def isDirPath(path):
	""" Returns true if the path is a directory (ends with / or \\). """
	return path and (path[-1] in ('/', '\\'))


__longPathCache = {} # GIL protects integrity of dict, no need for extra locking as it's only a cache
def toLongPathSafe(path, force=False):
	"""
	Converts the specified path string to a form suitable for passing to API 
	calls if it exceeds the maximum path length on this OS. 
	
	Currently, this is necessary only on Windows, where a unicode string 
	starting with \\?\ must be used to get correct behaviour for long paths. 
	
	Unlike L{normLongPath} which also performs the long path conversion, this 
	function does NOT convert to a canonical form, normalize slashes or 
	remove '..' elements (unless required for long path support). It is therefore 
	faster. 
	
	@param path: A path. Must not be a relative path. Can be None/empty. Can 
	contain ".." sequences. 
	
	@param force: Normally the long path support is added only if this path 
	exceeds the maximum length on this OS (e.g. 256 chars) or ends with a 
	directory slash. Set force to True to add long path support regardless of 
	length, which allows extra characters to be added on to the end of the 
	string (e.g. ".log" or a directory filename) safely. 
	
	@return The passed-in path, possibly with a \\?\ prefix added and 
	forward slashes converted to backslashes on Windows. Any trailing slash 
	is preserved by this function (though will be converted to a backslash). 
	"""
	if (not __isWindows) or (not path): return path
	if (force or len(path)>255 or isDirPath(path)) and not path.startswith('\\\\?\\'):
		
		if path in __longPathCache: return __longPathCache[path]
		inputpath = path
		# ".." is not permitted in \\?\ paths; normpath is expensive so don't do this unless we have to
		if '..' in path: 
			path = os.path.normpath(path)+('\\' if isDirPath(path) else '') 
		else:
			# path is most likely to contain / so more efficient to conditionalize this 
			path = path.replace('/','\\')

		try:
			if path.startswith('\\\\'): 
				path = u'\\\\?\\UNC\\'+path.lstrip('\\') # \\?\UNC\server\share Oh My
			else:
				path = u'\\\\?\\'+path
		except Exception:
			# can throw an exception if path is a bytestring containing non-ascii characters
			# to be safe, fallback to original string, just hoping it isn't both 
			# international AND long
			# could try converting using a default encoding, but slightly error-prone
			pass 
		__longPathCache[inputpath]  = path
	return path

__normLongPathCache = {} # GIL protects integrity of dict, no need for extra locking as it's only a cache
	
def normLongPath(path):
	"""
	Normalizes and absolutizes a path (os.path.abspath), converts to a canonical 
	form (e.g. normalizing the case of the drive letter on Windows), and on 
	windows adds the \\?\ prefix needed to force correct handling of long 
	(>256 chars) paths (same as L{toLongPath}). 
	
	@param path: the absolute path to be converted should be a unicode string where possible, as specifying a byte 
	string will not work if the path contains non-ascii characters. 
	"""
	if not path: return path
	
	# profiling shows normLongPath is surprisingly costly; caching results reduces dep checking by 2-3x
	if path in __normLongPathCache: return __normLongPathCache[path]
	inputpath = path
	# currently there is some duplication between this and buildcommon.normpath which we ought to fix at some point
	
	# normpath does nothing to normalize case, and windows seems to be quite random about upper/lower case 
	# for drive letters (more so than directory names), with different cmd prompts frequently using different 
	# capitalization, so normalize at least that bit, to prevent spurious rebuilding from different prompts
	if __isWindows and len(path)>2 and path[1] == ':' and path[0] >= 'A' and path[0] <= 'Z': 
		path = path[0].lower()+path[1:]
		
	if __isWindows and path and path.startswith('\\\\?\\'):
		path = path.replace('/', '\\')
	else:
		# abspath also normalizes slashes
		path = os.path.abspath(path)+(os.path.sep if isDirPath(path) else '')
		
		if __isWindows and path and not path.startswith('\\\\?\\'):
			try:
				if path.startswith('\\\\'): 
					path = u'\\\\?\\UNC\\'+path.lstrip('\\') # \\?\UNC\server\share Oh My
				else:
					path = u'\\\\?\\'+path
			except Exception:
				# can throw an exception if path is a bytestring containing non-ascii characters
				# to be safe, fallback to original string, just hoping it isn't both 
				# international AND long
				# could try converting using a default encoding, but slightly error-prone
				pass 
	__normLongPathCache[inputpath] = path
	return path
	
__statcache = {}
def getstat(path):
	""" Cached-once os.stat (DO NOT USE if you expect it to change after startup) """
	st = __statcache.get(path, None)
	if None == st:
		try:
			st = os.stat(path)
		except os.error: # mean file doesn't exist
			st = False

		__statcache[path] = st
	return st

def getmtime(path):
	""" Cached-once os.getmtime (DO NOT USE if you expect it to change after startup) """
	return getstat(path).st_mtime
def getsize(path):
	""" Cached-once os.path.getsize (DO NOT USE if you expect it to change after startup) """
	return getstat(path).st_size
def exists(path):
	""" Cached-once os.path.exists (DO NOT USE if you expect it to change after startup) """
	return getstat(path) != False
def isfile(path):
	""" Cached-once os.path.isfile (DO NOT USE if you expect it to change after startup) """
	st = getstat(path)
	return st and stat.S_ISREG(st.st_mode)
def isdir(path):
	""" Cached-once os.path.isdir (DO NOT USE if you expect it to change after startup) """
	st = getstat(path)
	return st and stat.S_ISDIR(st.st_mode)

def resetStatCache():
	""" Resets cached stat data """
	__statcache.clear()

# terminal functions
# 
# Copyright (c) 2015 - 2017 Software AG, Darmstadt, Germany and/or its licensors
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
# $Id: terminal.py 301527 2017-02-06 15:31:43Z matj $
#

"""
Utility functions for getting information about the stdout terminal, which may be useful when implementing 
console formatters. 
"""

def getTerminalSize():
	""" getTerminalSize()
	 - get width and height of console
	 - works on linux,os x,windows,cygwin(windows)
	"""
	import platform
	current_os = platform.system()
	tuple_xy=None
	if current_os == 'Windows':
		tuple_xy = _getTerminalSize_windows()
		if tuple_xy is None:
			tuple_xy = _getTerminalSize_tput()
			# needed for window's python in cygwin's xterm!
	if current_os == 'Linux' or current_os == 'Darwin' or  current_os.startswith('CYGWIN'):
		tuple_xy = _getTerminalSize_linux()
	if tuple_xy is None:
		print("default")
		tuple_xy = (80, 25)   # default value
	return tuple_xy

def _getTerminalSize_windows():
	res=None
	try:
		from ctypes import windll, create_string_buffer

		# stdin handle is -10
		# stdout handle is -11
		# stderr handle is -12

		h = windll.kernel32.GetStdHandle(-12)
		csbi = create_string_buffer(22)
		res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
	except:
		return None
	if res:
		import struct
		(bufx, bufy, curx, cury, wattr, left, top, right, bottom, maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
		sizex = right - left + 1
		sizey = bottom - top + 1
		return sizex, sizey
	else:
		return None

def _getTerminalSize_tput():
	# get terminal width
	# src: http://stackoverflow.com/questions/263890/how-do-i-find-the-width-height-of-a-terminal-window
	try:
		import subprocess
		proc=subprocess.Popen(["tput", "cols"],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
		output=proc.communicate(input=None)
		cols=int(output[0])
		proc=subprocess.Popen(["tput", "lines"],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
		output=proc.communicate(input=None)
		rows=int(output[0])
		return (cols,rows)
	except Exception:
		return None


def _getTerminalSize_linux():
	def ioctl_GWINSZ(fd):
		try:
			import fcntl, termios, struct, os
			cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,'1234'))
		except:
			return None
		return cr
	cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
	if not cr:
		try:
			fd = os.open(os.ctermid(), os.O_RDONLY)
			cr = ioctl_GWINSZ(fd)
			os.close(fd)
		except:
			pass
	if not cr:
		try:
			cr = (env['LINES'], env['COLUMNS'])
		except:
			return None
	return int(cr[1]), int(cr[0])


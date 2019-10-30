# xpyBuild - eXtensible Python-based Build System
#
# This class is responsible for working out what tasks need to run, and for 
# scheduling them
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
# $Id: stacktrace.py 301527 2017-02-06 15:31:43Z matj $
#

import traceback, signal, sys, threading

from buildcommon import isWindows

def print_stack_trace(sig, frame):
	"""Dump a python stack trace to stderr on a signal"""

	sys.stderr.write('\nTraceback:\n')
	sys.stderr.flush()
	id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
	code = []
	for threadId, stack in sys._current_frames().items():
		sys.stderr.write("\n# Thread: %s(%d)\n" % (id2name.get(threadId, ""), threadId))
		for filename, lineno, name, line in traceback.extract_stack(stack):
			sys.stderr.write('\tFile: "%s", line %d, in %s\n' % (filename, lineno, name))
			if line:
				sys.stderr.write('\t\t%s\n' % line.strip())
		sys.stderr.flush()

def listen_for_stack_signal():
	if not isWindows():
		signal.signal(signal.SIGUSR1, print_stack_trace)

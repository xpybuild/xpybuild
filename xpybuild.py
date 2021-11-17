#!/usr/bin/env python3
#
# Launcher script for xpybuild, the eXtensible Python-based Build System
#
# Copyright (c) 2013 - 2019 Software AG, Darmstadt, Germany and/or its licensors
# Copyright (c) 2013 - 2019 Ben Spiller and Matthew Johnson
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
#
# $Id: xpybuild.py 305815 2017-04-13 17:20:20Z bsp $
#

import sys, os

if __name__ == "__main__":
	xpybuild_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'xpybuild'))
	if not os.path.exists(xpybuild_dir): sys.exit('xpybuild not found in: '+xpybuild_dir)
	xpybuild_dir = os.path.dirname(xpybuild_dir)
	if xpybuild_dir not in sys.path: sys.path.append(xpybuild_dir)
	from xpybuild.__main__ import main
	sys.exit(main(sys.argv[1:]))

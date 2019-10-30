#
# Copyright (c) 2019 Software AG, Darmstadt, Germany and/or its licensors
# Copyright (c) 2019 Ben Spiller and Matthew Johnson
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

import sys, os

# this is deliberately a valid Python v2 AND v3 script so we can warn the user if they mess this up
if float(sys.version[:3]) < 3.6: sys.exit('xpybuild.py requires at least Python 3.6 - unsupported Python version %s'%sys.version[:3])

# for now, allow accessing the contents of the xpybuild package both with and without "xpybuild." qualification
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.dirname(__file__))

from xpybuild.internal.main import main
sys.exit(main(sys.argv[1:]))
# This is only for use by legacy proprietary launcher scripts that use "import xpybuild; xpybuild.main(...)"
import sys as __sys
if 'sphinx' not in __sys.argv[0]:
	from xpybuild.__main__ import main

from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.java import *
import logging

Javac('${OUTPUT_DIR}/test-source-target/', ['./Simple.java'], []).option('javac.source', '7').option('javac.target', '8')

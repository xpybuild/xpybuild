from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.java import *
import logging

Javac('${OUTPUT_DIR}/test-warnings/', ['./JavaWarnings.java'], []).option('javac.options', ['-Xlint'])

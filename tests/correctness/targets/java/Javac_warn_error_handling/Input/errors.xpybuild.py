from xpybuild.propertysupport import *
from xpybuild.buildcommon import *
from xpybuild.pathsets import *

from xpybuild.targets.java import Jar
import logging

# also useful to test with the jar target since the jar executable munges it further
Jar('${OUTPUT_DIR}/test-errors.jar', ['./JavaErrors.java'], [], manifest={})

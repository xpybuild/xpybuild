from propertysupport import *
from buildcommon import *
from pathsets import *

from targets.java import *
import logging

Javac('${OUTPUT_DIR}/test-warnings/', ['./JavaWarnings.java'], []).option('javac.options', ['-Xlint'])

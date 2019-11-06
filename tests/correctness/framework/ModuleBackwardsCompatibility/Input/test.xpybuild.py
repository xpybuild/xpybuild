from xpybuild.propertysupport import enableLegacyXpybuildModuleNames
enableLegacyXpybuildModuleNames()

import os, logging

from propertysupport import *
from buildcommon import *

import pathsets as oldpathsets
import xpybuild.pathsets as newpathsets

# deliberately use old names
from targets.writefile import WriteFile
from targets.copy import Copy

defineOutputDirProperty('OUTPUT_DIR', None)

WriteFile('${OUTPUT_DIR}/foo.txt', 'Hello world')

# this is to check that the isinstance checks used by PathSet are working right - new and old package names should not have different pathsets! If they do, this will error. 
Copy('${OUTPUT_DIR}/copy1/', newpathsets.PathSet(oldpathsets.PathSet('${OUTPUT_DIR}/foo.txt')))
Copy('${OUTPUT_DIR}/copy2/', oldpathsets.PathSet(newpathsets.PathSet('${OUTPUT_DIR}/foo.txt')))

# check that names from before v3.0 still work and map to the new names
import xpybuild.buildcontext
assert xpybuild.buildcontext.getBuildInitializationContext() == xpybuild.buildcontext.BuildInitializationContext.getBuildInitializationContext()

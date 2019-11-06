from xpybuild.propertysupport import enableLegacyXpybuildModuleNames
enableLegacyXpybuildModuleNames()

import os, logging
from propertysupport import *
from buildcommon import *
from pathsets import *
from targets.copy import Copy

defineOutputDirProperty('OUTPUT_DIR', None)

Copy('${OUTPUT_DIR}/target%d/'%1, PathSet([
		PathSet(),
		FindPaths('${OUTPUT_DIR}/../findpathsroot/', 
			includes=[
				'1/*/*iii*', # deep - so that first directory excluder doesn't fire for it
				'*1/**', '2/a*/**/'],  # do not navigate into 3  (nb: avoid no ** prefixes since that disables unmatched dir handler)
			excludes=['**/b/**', '1/c/**/'] # do not navigate into b\
			)
		])
	)

Copy('${OUTPUT_DIR}/target%d/'%2, [FindPaths('${OUTPUT_DIR}/../findpathsroot/', 
		includes=['1/*/*', # this is to check for a path longer than non-doublestar pattern, with somefile
		'**/*i*', '**/'],  # should disable dir exclusion logic for includes
		excludes=['*/*b*/**', '*/*b*/**/'] # do not navigate into b/
		)])


Copy('${OUTPUT_DIR}/target%d/'%3, [FindPaths('${OUTPUT_DIR}/../findpathsroot/', 
		#includes= do not set - should be treated as all files
		excludes=['**/'] # these wouldn't be included anyway to be fair
		)])

Copy('${OUTPUT_DIR}/target%d/'%4, [FindPaths('${OUTPUT_DIR}/../findpathsroot/', 
		includes='**/' # just empty dirs
		#excludes=  do not set
		)])

Copy('${OUTPUT_DIR}/target%d/'%5, [FindPaths('${OUTPUT_DIR}/../findpathsroot/', 
		includes='1/**/' # triggers directory walk excluder that uses directory names
		#excludes=  do not set
		)])

try:
	Copy('${OUTPUT_DIR}/target-bad/', [FindPaths('${OUTPUT_DIR}/../findpathsroot/', 
			includes='a/**b**/c',
			)])
except Exception as e:
	import logging
	logging.getLogger('testing').critical('Got exception as expected from FindPaths: %s'%e)


import os
from propertysupport import *
from buildcommon import *
from pathsets import *

defineOutputDirProperty('OUTPUT_DIR', None)

import basetarget 
defineOption('mydefopt', 'myval')
defineOption('myopt', 'orig-shouldnotsee')
defineOption('staticopt', 'orig')
defineOption('staticopt2', 'orig')
defineOption('dynopt', 'orig')
setGlobalOption('myopt', 'myval')

defineOption('testoption.default', 'expectedval')
defineOption('testoption.globalOverride', 'unexpectedval')
setGlobalOption('testoption.globalOverride', 'expectedval')

defineOption('testoption.targetOverride', 'defaultval')

defineOption('testoption.legacyTargetOverride', 'defaultval')


class MyTarget(basetarget.BaseTarget):
	def __init__(self, name, options=None):
		super(MyTarget, self).__init__(name, [])
		if options:
			# this is no longer recommended practice, but need to maintain it for backwards compat
			self.options = options
		
	def run(self, context):
		name = os.path.basename(self.path)
		
		with open(self.path, 'w') as f:
			def printit(o, display):
				for k in sorted(o.keys()):
					if k.startswith('testoption.'): 
						self.log.critical('-- %s %s=%s', display, k, o[k])
						print >>f, '%s %s=%s'%(display, k, o[k])
		
			printit(self.options, name+' self.options')
			printit(context.mergeOptions(self), name+' mergeOptions')
		
	def clean(self, context): pass

MyTarget('${OUTPUT_DIR}/defaults.txt')
MyTarget('${OUTPUT_DIR}/legacyTargetOverride.txt', options={'testoption.legacyTargetOverride':'expectedval'})
MyTarget('${OUTPUT_DIR}/targetOverride.txt').option('testoption.targetOverride', 'expectedval')

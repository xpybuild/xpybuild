import os, logging
from propertysupport import *
from buildcommon import *
from pathsets import *

defineOutputDirProperty('OUTPUT_DIR', None)

import basetarget 

defineStringProperty('MY_PROP', 'expectedval')

defineOption('testoption.default', '${MY_PROP}')
defineOption('testoption.globalOverride', 'unexpectedval')
setGlobalOption('testoption.globalOverride', 'expectedval')

defineOption('testoption.targetOverride', 'defaultval')

defineOption('testoption.legacyTargetOverride', 'defaultval')

defineOption('testoption2.empty', '')

class CustomPathSet(BasePathSet):
	def __init__(self, *args):
		BasePathSet.__init__(self)
		self.delegate = PathSet(*args)
	def resolveWithDestinations(self, context):
		assert self.target.options
		return self.delegate.resolveWithDestinations(context)
	def _resolveUnderlyingDependencies(self, context):
		# this might be needed in some targets, so check it works
		assert self.target.options
		logging.getLogger('custompathset').critical('PathSet._resolveUnderlyingDependencies got options: %s', self.target.options)
		return self.delegate._resolveUnderlyingDependencies(context)

class MyTarget(basetarget.BaseTarget):
	def __init__(self, name, options=None, deps=[]):
		super(MyTarget, self).__init__(name, dependencies=deps)
		
		if options:
			# this is no longer recommended practice, but need to maintain it for backwards compat
			self.options = options

		try:
			x = self.options
			self.log.error('ERROR - should be impossible to read self.options in the constructor unexpectedly: %s', x)
		except Exception, e:
			self.log.critical('Exception from trying to read self.options: %s'%e)
		
	def run(self, context):
		name = os.path.basename(self.path)
		
		with open(self.path, 'w') as f:
			def printit(o, display):
				for k in sorted(o.keys()):
					if k.startswith('testoption.'): 
						self.log.critical('-- %s %s=%s', display, k, o[k])
						print >>f, '%s %s=%s'%(display, k, o[k])
		
			printit(context.mergeOptions(self), name+' mergeOptions')
			assert context.mergeOptions(self) == self.options, '%s != %s'%(context.mergeOptions(self), self.options)
			self.log.critical('-- %s getOption %s=%s', name, 'testoption.default', self.getOption('testoption.default'))
			
			try:
				self.getOption('testoption2.empty')
				self.log.error('ERROR - getOption should throw if empty')
			except Exception, e:
				self.log.critical('Got expected exception: %s', e)
			
			
	def getHashableImplicitInputs(self, context):
		assert self.options
		return [str(self.options)]
		
	def clean(self, context): 
		pass

pathset = CustomPathSet('test.xpybuild.py')
t = MyTarget('${OUTPUT_DIR}/defaults.txt', deps=pathset)
pathset.target = t

MyTarget('${OUTPUT_DIR}/legacyTargetOverride.txt', options={'testoption.legacyTargetOverride':'${MY_PROP}'})
MyTarget('${OUTPUT_DIR}/targetOverride.txt').option('testoption.targetOverride', 'expectedval')
# do both and check .option(...) takes precedence
MyTarget('${OUTPUT_DIR}/targetOverrideBoth.txt', options={'testoption.targetOverride':'unexpectedval'}).option('testoption.targetOverride', 'expectedval')

from xpybuild.buildcommon import enableLegacyXpybuildModuleNames
enableLegacyXpybuildModuleNames() # having this turned on is useful - importing extra modules may give extra errors

import os, logging
from propertysupport import *
from buildcommon import *
from pathsets import *

# not used below, but make sure they're imported as they're the ones most likely to trigger unhelpful 0xYYYYY addresses in implicit input files
import targets.native
import targets.custom
import targets.java
import targets.copy

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
		assert self.target.options, self.target.options
		
		assert context.getGlobalOption('testoption.globalOverride')=='expectedval', context.getGlobalOption('testoption.globalOverride')
		assert context.getGlobalOption('testoption.targetOverride')=='defaultval', context.getGlobalOption('testoption.targetOverride')
		
		return self.delegate.resolveWithDestinations(context)
	def _resolveUnderlyingDependencies(self, context):
		# this might be needed in some targets, so check it works
		assert self.target.options, self.target.options
		logging.getLogger('custompathset').critical('PathSet._resolveUnderlyingDependencies got options: %s', self.target.options)

		assert context.getGlobalOption('testoption.globalOverride')=='expectedval', context.getGlobalOption('testoption.globalOverride')
		assert context.getGlobalOption('testoption.targetOverride')=='defaultval', context.getGlobalOption('testoption.targetOverride')

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
		except Exception as e:
			self.log.critical('Got exception as expected from trying to read self.options during constructor: %s'%e)
		
		# include every option, just to show we can
		self.addHashableImplicitInputOption(lambda optionKey: optionKey!='testoption.default')
		self.addHashableImplicitInputOption('testoption.default')
		
		self.addHashableImplicitInput(lambda context: f'addHashableImplicitInput called with {context.__class__.__name__}')
		self.addHashableImplicitInput(lambda context: None)
		self.addHashableImplicitInput('addHashableImplicitInput str ${MY_PROP}')
		#self.addHashableImplicitInput(['addHashableImplicitInput list', 'item2'])
		
	def run(self, context):
		name = os.path.basename(self.path)
		
		with open(self.path, 'w') as f:
			def printit(o, display):
				for k in sorted(o.keys()):
					if k.startswith('testoption.'): 
						self.log.critical('-- %s %s=%s', display, k, o[k])
						print('%s %s=%s'%(display, k, o[k]), file=f)
		
			printit(context.mergeOptions(self), name+' mergeOptions')
			assert context.mergeOptions(self) == self.options, '%s != %s'%(context.mergeOptions(self), self.options)
			self.log.critical('-- %s getOption %s=%s', name, 'testoption.default', self.getOption('testoption.default'))
			
			try:
				self.getOption('testoption2.empty')
				self.log.error('ERROR - getOption should throw if empty')
			except Exception as e:
				self.log.critical('Got expected exception: %s', e)
			
			
	def getHashableImplicitInputs(self, context):
		assert self.options
		return super().getHashableImplicitInputs(context)
		
	def clean(self, context): 
		pass

pathset = CustomPathSet('test.xpybuild.py')
t = MyTarget('${OUTPUT_DIR}/defaults.txt', deps=pathset)
pathset.target = t

MyTarget('${OUTPUT_DIR}/legacyTargetOverride.txt', options={'testoption.legacyTargetOverride':'${MY_PROP}'})
MyTarget('${OUTPUT_DIR}/targetOverride.txt').option('testoption.targetOverride', 'expectedval')
# do both and check .option(...) takes precedence
MyTarget('${OUTPUT_DIR}/targetOverrideBoth.txt', options={'testoption.targetOverride':'unexpectedval'}).option('testoption.targetOverride', 'expectedval')

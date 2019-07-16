from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest

class PySysTest(XpybuildBaseTest):

	def execute(self):
		# run single threaded so we can look at order
		self.xpybuild(args=['-j1'])

	def validate(self):
		selectedtargets = 'build-output/BUILD_WORK/targets/selected-targets.txt'

		for target, priority in [
			('testtarget1', '0.0'),
			('testtarget2/', '15.1'), 
			('testtarget2a', '16.1'), # increased by dependency
			('testtarget2b', '20.2'), # not affected by dependency as already bigger
			('testtarget3/', '16.1'), 
			('testtarget4/', '0.5'),
			('testtarget5', '1'), # an integer
			('testtarget6', '0.0'),
		]:
			self.assertGrep(selectedtargets, expr='Target .*%s .*with priority %s '%(target, priority))

		# check we build in descending priority order. note that order within priority buckets is not defined
		# check the partial orderings that matter
		self.assertOrderedGrep('xpybuild.log', exprList=[
			'CRITICAL .* Building .*%s'%s for s in [
				'testtarget2b', #20.2
				#'testtarget2a', #16.1
				'testtarget3/', # 16.1
				'testtarget2/',#15.1
				'testtarget4/',#0.5
				'testtarget1',#0.0
				#'testtarget6',#0.0
			]
		])

		self.assertOrderedGrep('xpybuild.log', exprList=[
			'CRITICAL .* Building .*%s'%s for s in [
				'testtarget2b', #20.2
				'testtarget2a', #16.1
				#'testtarget3/', # 16.1
				'testtarget2/',#15.1
				'testtarget4/',#0.5
				#'testtarget1',#0.0
				'testtarget6',#0.0
			]
		])
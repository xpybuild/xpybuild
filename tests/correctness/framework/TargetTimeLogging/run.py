from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest
import multiprocessing
import os, csv, re

class PySysTest(XpybuildBaseTest):

	def execute(self):
		self.xpybuild(args=['--timefile', 'timefile-output', 
			'--cpu-stats'])

	def validate(self):
		# check critical path
		self.assertOrderedGrep('xpybuild.log', exprList=[
				r'Critical Path is:',
				r'\${OUTPUT_DIR}/sleep[AB] \([0-9\.]*, [0-9\.]*\)',
				r'\${OUTPUT_DIR}/sleepC \([0-9\.]*, [0-9\.]*\)',
				r'\${OUTPUT_DIR}/sleepD \([0-9\.]*, [0-9\.]*\)',
				r'\${OUTPUT_DIR}/sleepH \([0-9\.]*, [0-9\.]*\)',
				r'\${OUTPUT_DIR}/sleepI \([0-9\.]*, [0-9\.]*\)',
				r'\${OUTPUT_DIR}/sleepJ \([0-9\.]*, [0-9\.]*\)',
			])
		
		# check target appears with ,
		self.assertGrep('timefile-output.csv', expr='${OUTPUT_DIR}/testtarget4/,', literal=True)

		# check dependencies in dot
		self.assertGrep('timefile-output.dot', expr='testtarget2b -> .*testtarget4')
		
		# check , in input name doesn't break csv
		self.assertGrep('timefile-output.csv', expr='test_target5')

		self.logFileContents('xpybuild.log', maxLines=0) # temporary to see what's going on in travis

		# check header and times roughly correct
		N = 1.39728
		NAME=0
		TIME=1
		SUM=2
		CRIT=3
		with open(os.path.join(self.output, 'timefile-output.csv')) as f:
			csv_reader = csv.reader(f, delimiter=',')
			header = True
			maxcrit = 0
			maxcritname = ""
			for row in csv_reader:
				if header:
					header = False
					self.assertTrue(row[NAME]=='Target', assertMessage="Header row is Target")
					self.assertTrue(row[TIME]=='Time', assertMessage="Header row is Time")
					self.assertTrue(row[SUM]=='Cumulative', assertMessage="Header row is Cumulative")
					self.assertTrue(row[CRIT]=='Critical Path', assertMessage="Header row is Critical Path")
				else:
					# check target name
					self.assertEval('re.match({expression},{value})', expression=r'^\$\{OUTPUT_DIR\}/(sleep[A-J]|test_?target[0-9]).*$', value=row[NAME])

					# check times are numbers
					for i in range(1,4):
						self.assertEval('re.match({expression},{value})', expression=r'^[0-9]+\.[0-9]+$', value=row[i])
						row[i] = float(row[i])
					
					# check time is about right
					if 'sleep' in row[NAME]:
						fudgefactor = 0.4 # needs to be fairly large to cope with running on TravisCI
						self.assertTrue(row[TIME] < N+fudgefactor and row[TIME] > N-fudgefactor, assertMessage=f"Time for row {row[NAME]} wasn't N={N} +/-{fudgefactor} (it was {row[TIME]})")

					# find largest crit
					if row[CRIT] > maxcrit:
						maxcrit = row[CRIT]
						maxcritname = row[NAME]

					# leaf node everything should be the same
					if 'sleepA' in row[NAME]:
						self.assertEval('{a}=={b}', a=row[TIME], b=row[CRIT])
						self.assertEval('{a}=={b}', a=row[TIME], b=row[SUM])
					# target with multiple dependencies should be all different
					# and time < crit < sum
					if 'sleepC' in row[NAME]:
						self.assertEval('{a}<{b}', a=row[TIME], b=row[SUM])
						self.assertEval('{a}<{b}', a=row[TIME], b=row[CRIT])
						self.assertEval('{a}<{b}', a=row[CRIT], b=row[SUM])
					# target with lots of overlapping dependencies has sum about right
					if 'sleepG' in row[NAME]:
						self.assertTrue(row[SUM] < 7*N+1 and row[SUM] > 7*N-1, assertMessage="sleepG's cumulative time is 7*N +/- 1 (it was %s)"%row[SUM])
						self.assertTrue(row[CRIT] < 4*N+1 and row[CRIT] > 4*N-1, assertMessage="sleepG's crit time is 4*N +/- 1 (it was %s)"%row[CRIT])
					
			# critical path is correct target and about the right time
			self.assertTrue('sleepJ' in maxcritname, assertMessage="sleepJ is the critical path (it was %s/%s)" % (maxcritname, maxcrit))
			self.assertTrue(maxcrit < 6*N+1 and maxcrit > 6*N-1, assertMessage="Critical path is 6*N +/- 1 (it was %s)" % maxcrit)

		# check cpu stats
		self.logFileContents('xpybuild.log', maxLines=0)
		self.assertOrderedGrep('xpybuild.log', exprList=[
				r'Utilisation average: 01\.[0-9]*/%d'%multiprocessing.cpu_count(),
				r'Utilisation histogram:',
				r'1\] \([0-9\.]*[1-9][0-9\.]*%\) ==============',
				r'2\] \([0-9\.]*[1-9][0-9\.]*%\) ==========',
				r'3\] \([0-9\.]*[1-9][0-9\.]*%\) ======',
			])


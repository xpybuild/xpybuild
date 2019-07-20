import glob
import subprocess
import logging, io, sys
import multiprocessing
from pysys.utils.perfreporter import *
from pysys.utils.logutils import ColorLogFormatter
from pysys.utils.logutils import stdoutPrint
from pysys.constants import PROJECT

def getXpybuildVersion(project):
	assert project, 'not initialized yet'
	with io.open(project.XPYBUILD_ROOT+'/XPYBUILD_VERSION', encoding='ascii') as f:
		return f.read().strip()

_log = logging.getLogger('perfreporter')

class XpybuildPerfReporter(CSVPerformanceReporter):
	def __init__(self, project, summaryfile, testoutdir):
		self.XPYBUILD_VERSION = getXpybuildVersion(project)

		super(XpybuildPerfReporter, self).__init__(project, summaryfile or 'performance_output/v'+self.XPYBUILD_VERSION+'/@OUTDIR@_@HOSTNAME@/perf_@DATE@_@TIME@.csv', testoutdir)
		self.unitAliases['ns'] = PerformanceUnit('ns', biggerIsBetter=False)
		
		self.disableRecording = ('XPYBUILD_PPROFILE' in os.environ)# or (getattr(self, 'DISABLE_PERF_RECORDING','')=='true')
		
		self.__recordedPerformanceLines = [self.getRunHeader()]
		
	def getRunDetails(self):
		d = super(XpybuildPerfReporter, self).getRunDetails()
		d['xpybuildVersion'] = self.XPYBUILD_VERSION
		
		try:
			gitcommit = subprocess.check_output(['git', 'show', '-s', '--format=%h']).strip()
			assert '\n' not in gitcommit, gitcommit
		except Exception as ex:
			_log.debug('Failed to get git commit hash: %s', ex)
		else:
			d['gitCommit'] = gitcommit

		d['cpuCount'] = multiprocessing.cpu_count()		
		d['platform'] = sys.platform
		return d

	def recordResult(self, formatted, testobj):
		if self.disableRecording: return
		self.__recordedPerformanceLines.append(formatted)
		super(XpybuildPerfReporter, self).recordResult(formatted, testobj)
	
	def cleanup(self):
		try:
			thisRun = CSVPerformanceFile('\n'.join(self.__recordedPerformanceLines))
			thisRun.label = 'this'
			# maybe compare to previous runs - just textual
			comp = os.getenv('PYSYS_PERFORMANCE_BASELINES', '')
			if comp and thisRun.results:
				comp = comp.split(',')
				for l in comparePerformanceFiles(comp+[thisRun], sortby='comparison%').strip().split('\n'):
					stdoutPrint(l) # need to keep separate for coloring to work
			
		finally:
			super(XpybuildPerfReporter, self).cleanup()

# The lines below here should probably be contributed to pysys perfreporter.py eventually
			

def expandPathSpecifier(pathspecifier): # want a better name for this probably
	""" Returns {'pathspecifier':..., label:... or None, filenames: [filelist], files=[CSVPerformanceFile...]}. 
	Expands directories, glob patterns, and filters by @latest if specified. """
	p = pathspecifier.strip()
	latest = p.lower().endswith('@latest')
	if latest: p = p[:-len('@latest')]
	if '=' in p:
		label, p = p.split('=', 1)
	else:
		label, p = None, p
	paths = glob.glob(p)
	if not paths: raise Exception('No matching paths for glob expression %s'%(p))
	result = []
	for p in paths:
		p = os.path.normpath(p)
		if not os.path.isdir(p):
			result.append(p)
		else:
			for (dirpath, dirnames, filenames) in os.walk(p):
				for f in filenames:
					if f.endswith('.csv'):
						result.append(dirpath+'/'+f)
			if not result:
				raise Exception('No .csv files found in %s'%p)

	# sorted in modification time order is most helpful
	result = sorted(result, key=lambda p: os.path.getmtime(p))
	if latest:
		result = [result[-1]]
	_log.debug('Converted pathspecifier "%s" to label="%s", files=%s', pathspecifier, label, result)
	
	parsedfiles = []
	for fname in result:
		try:
			with io.open(fname) as fhandle:
				parsedfiles.append(CSVPerformanceFile(fhandle.read()))
		except Exception as ex:
			raise Exception('Failed to read performance file %s: %s'%(fname, ex))
	return {'pathspecifier':pathspecifier, 'label':label, 'filenames':result, 'files':parsedfiles}

LOG_PERF_BETTER = 'performancebetter'
LOG_PERF_WORSE = 'performanceworse'

def comparePerformanceFiles(compareList, format='text', sortby='comparison%'):
	"""
	Compare one or more baseline files against the latest. 
	
	@param compareList: a list, where each is either a CVSPerformanceFile object 
	(with its label attribute optionally set) or 
	a path specifier string (a file or directory of CVS files, with 
	glob and optional @latest filter). Labels can be specified as LABEL=specifier. 
	
	"""
	assert format == 'text' # will support CVS soon

	# we don't have the project available here, but can still reuse the same 
	# logic for deciding if coloring is enabled
	colorFormatter = ColorLogFormatter({
		'color:'+LOG_PERF_BETTER:'GREEN',
		'color:'+LOG_PERF_WORSE:'RED',
	})

	i = -1
	files = [] # list of CSVPerformanceFile instance which we'll add extra data to
	for p in compareList:
		i+=1
		if isinstance(p, CSVPerformanceFile):
			p.numberOfFiles = getattr(p, 'numberOfFiles', 1)
			p.index = i
			files.append(p)
		elif isstring(p):
			expanded = expandPathSpecifier(p)
			p = CSVPerformanceFile.aggregate(expanded['files'])
			p.index = i
			p.label = expanded['label']
			p.numberOfFiles = len(expanded['files'])
			files.append(p)			
		else:
			assert False, 'unknown type: %s: %s'%(type(p), p)

	def addColor(category, s):
		if not category: return s
		return colorFormatter.formatArg(category, s) 
			
	output = ['']
	try:
		def out(s):
			output[0] += '%s\n'%s
		
		# usually resultKey is itself the unique key, but for comparisons we also 
		# want to include units/biggerIsBetter since if these change the 
		# comparison would be invalidated
		ComparisonKey = collections.namedtuple('ComparisonKey', ['resultKey', 'unit', 'biggerIsBetter'])

		# iterate over each comparison item, stashing various aggregated information we need later, and printing summary info
		for p in files:
			p.keyedResults = {
				ComparisonKey(resultKey=r['resultKey'], unit=r['unit'], biggerIsBetter=r['biggerIsBetter'])
				: r for r in p.results
			}

		# end iteration over paths
		commonRunDetails = collections.OrderedDict()
		for k in list(files[-1].runDetails.keys()):
			if all([k in p.runDetails and  p.runDetails[k] == files[-1].runDetails[k] for p in files]):
				commonRunDetails[k] = files[-1].runDetails[k]

		def formatRunDetails(k, val):
			valsplit = val.split(';')
			if k=='time' and len(valsplit)>3:
				val = ' .. '.join([valsplit[0].strip(), valsplit[-1].strip()])
			else:
				val = val.replace('; ',';')
			return '%s=%s'%(k, addColor(LOG_TEST_DETAILS, val))

		out('Common run details: %s'%', '.join([formatRunDetails(k, commonRunDetails[k]) for k in commonRunDetails]))

		out('Comparing: ')
			
		for p in files:
			out('- %s (%d results, %d samples/result, from %d files):'%(
				addColor(LOG_TEST_DETAILS, p.label or '#%d'%(p.index+1)), 
				len(p.results), 
				float( sum([r['samples'] for r in p.results])) / len(p.results),
				p.numberOfFiles, 
				))
			out('   %s'%', '.join([formatRunDetails(k, p.runDetails[k]) for k in p.runDetails if k not in commonRunDetails]))
			out('')

		
		ComparisonData = collections.namedtuple('ComparisonData', ['comparisonPercent', 'comparisonSigmas', 
			'ratio', 'rfrom', 'rto'])
		
		# now compute comparison info, comparing each path to the final one
		comparisons = {} # ComparisonKey:[ComparisonInfo or string if not available, ...]
		comparetoresults = files[-1].keyedResults
		comparisonheaders = []
		for p in files[:-1]:
			if len(files)>2:
				comparisonheaders.append('%s->%s'%(p.label, files[-1].label))
			
			keyedResults = p.keyedResults
			for k in comparetoresults:
				c = comparisons.setdefault(k, [])
				if k not in keyedResults:
					c.append('Compare from value is missing')
				else:
					rfrom = keyedResults[k]
					rto = comparetoresults[k]
					# avoid div by zero errors; results are nonsensical anyway if either is zero
					if rfrom['value'] == 0: 
						c.append('Compare from value is zero')
						continue
					if rto['value'] == 0: 
						c.append('Compare to value is zero')
						continue

					# how many times faster are we now
					ratio = rto['value']/rfrom['value']
					# use a + or - sign to indicate improvement vs regression
					sign = 1.0 if k.biggerIsBetter else -1
					
					# frequently at least one of these will have only one sample so 
					# not much point doing a statistically accurate stddev estimate; so just 
					# take whichever is bigger (which neatly ignores any that are zero due
					# to only one sample)
					stddevRatio = max(abs(rfrom['stdDev']/rfrom['value']), abs(rto['stdDev']/rto['value']))
					
					comparisonPercent = 100.0*(ratio - 1)*sign
					# assuming a normal distribution, 1.0 or more gives 68% confidence of 
					# a real difference, and 2.0 or more gives 95%
					# this is effectively 
					comparisonSigmas = sign*((ratio-1)/stddevRatio) if stddevRatio else None
					
					c.append(ComparisonData(
						comparisonPercent=comparisonPercent, 
						comparisonSigmas=comparisonSigmas,
						ratio=ratio,
						rfrom=rfrom['value'], 
						rto=rto['value']
					))

		if comparisonheaders:
			headerpad = max([len(h) for h in comparisonheaders])
			comparisonheaders = [('%'+str(headerpad+1)+'s')%(h+':') for h in comparisonheaders]

		def getComparisonKey(k):
			if sortby == 'resultKey': return k
			if sortby == 'testId': return (allresultinfo[k]['testId'], k)
			# sort with regressions at the bottom, so they're more prominent
			if sortby == 'comparison%': return [
					(-1*c.comparisonPercent) if hasattr(c, 'comparisonPercent') else -10000000.0
					for c in comparisons[k]]+[k]
			assert False, sortby

		def addPlus(s):
			if not s.startswith('-'): return '+'+s
			return s

		def valueToDisplayString(value): # TODO: refactor this to avoid needing to copy
			"""Pretty-print an integer or float value to a moderate number of significant figures.
	
			The method additionally adds a "," grouping for large numbers.
	
			@param value: the value to be displayed
	
			"""
			if float(value) > 1000.0:
				return '{0:,}'.format(int(value))
			else:
				valtostr = '%0.4g' % value
				if 'e' in valtostr: valtostr = '%f'%value
				return valtostr
		sortedkeys = sorted(comparisons.keys(), key=getComparisonKey)
		
		for k in sortedkeys:
			out('%s from %s'%(colorFormatter.formatArg(LOG_TEST_PERFORMANCE, k.resultKey), files[-1].keyedResults[k]['testId']))
			i = 0
			for c in comparisons[k]:
				i+=1
				prefix = ('%s '%comparisonheaders[i-1]) if comparisonheaders else ''
				if not hasattr(c, 'comparisonPercent'):
					# strings for error messages
					out('  '+prefix+c)
					continue
				
				if c.comparisonSigmas != None:
					significantresult = abs(c.comparisonSigmas) >= (files[-1].keyedResults[k].get('toleranceStdDevs', 0.0) or 2.0)
				else:
					significantresult = abs(c.comparisonPercent) >= 10
				category = None
				if significantresult:
					category = LOG_PERF_BETTER if c.comparisonPercent > 0 else LOG_PERF_WORSE
				
				if c.comparisonSigmas is None:
					sigmas = ''
				else:
					sigmas = ' = %s sigmas'%addColor(category, addPlus('%0.1f'%c.comparisonSigmas))
				
				out('  '+prefix+'%s%s ( -> %s %s)'%(
					addColor(category, '%6s'%(addPlus('%0.1f'%c.comparisonPercent)+'%')), 
					sigmas, 
					valueToDisplayString(c.rto), 
					files[-1].keyedResults[k]['unit']
					))		
			out('')
		return output[0]
	except Exception as e:
		_log.info('Got exception, performance comparison output so far: \n%s'%output[0])
		raise

def _perfReporterMain(args):
	USAGE = """
python customperfreporter.py aggregate PATH1 PATH2... > aggregated.csv
python customperfreporter.py compare [--sort=SORTBY] COMPARE_OPTIONS [LABEL1=]PATH1 [LABEL2=]PATH2...

parameters:
  PATH - is a .csv file or directory of .csv files to be searched recursively. 
  may contain * glob expressions. 
  directory paths may end with the "@latest" suffix to select only the most 
  recent file. 

  LABEL - a short logical name to identify the results in a PATH, which will 
  be used in comparison column headings.
  
  SORTBY - how results should be sorted:
     resultKey - by the canonical resultKey name
     testId - by the testId
     comparison% - by the % increase/decrease

commands:
  aggregate - combines the specifies file(s) to form a single file 
  with one row for each resultKey, with the 'value' equal to the mean of all 
  values for that resultKey and the 'stdDev' updated with the standard deviation. 
  This can also be used with one or more .csv file to aggregate results from multiple 
  cycles. 
  
  compare - for each of two or more labelled PATHs, aggregates performance 
  results (if more than one) for each PATH and then produces a comparison 
  between them. If there are more than two paths then a comparison is generated 
  between each of the earlier ones and the final one. 
  Comparison results are written to stderr in textual form, and to stdout as 
  comma-separated values suitable for opening in a spreadsheet. 

Examples:
  aggregate ../performance_output@latest > aggregated.csv
  aggregate ../performance_output/beforefixes_*/ > aggregated.csv

  compare beforefixes_* currentrun_*@latest > before_and_after.csv
  compare original=beforefixes_* interim=somefixes_* latest=currentrun_*@latest > 3way_comparison.csv

"""
	if '-h' in sys.argv or '--help' in args or len(args) <2 or args[0] not in ['aggregate', 'compare']:
		sys.stderr.write(USAGE)
		sys.exit(1)
	
	cmd = args[0]
		
	verbosity = 'INFO'
	paths = [] # list of [pathspecifier, label or None, [filenames | CSVPerformanceFiles]]
	sortby = 'comparison%'
	
	VALID_SORT_OPTIONS = ['comparison%', 'testId', 'resultKey']
	for s in VALID_SORT_OPTIONS: assert s in USAGE, s
		
	for p in args[1:]:
		if p.startswith('-'):
			if p.startswith('--sort='):
				sortby = p[p.find('=')+1:]
			elif p.startswith('--verbosity='):
				verbosity = p[p.find('=')+1:]
			else:
				raise Exception('Unknown argument: %s'%p)
		else:
			paths.append(p)

	if sortby not in VALID_SORT_OPTIONS:
		raise Exception('Unknown sort argument: %s'%sortby)
	
	# send log output to stderr to avoid interfering with output we might be redirecting to a file	
	logging.basicConfig(format='%(levelname)s: %(message)s', stream=sys.stderr, level=getattr(logging, verbosity.upper()))
	
	
	if not paths:
		raise Exception('No .csv files found')

	if cmd == 'aggregate':
		parsed = [expandPathSpecifier(p)['files'] for p in paths]
		
		f = CSVPerformanceFile.aggregate([y for x in parsed for y in x])
		sys.stdout.write('# '+CSVPerformanceFile.toCSVLine(CSVPerformanceFile.COLUMNS+[CSVPerformanceFile.RUN_DETAILS, f.runDetails])+'\n')
		for r in f.results:
			sys.stdout.write(CSVPerformanceFile.toCSVLine(r)+'\n')
	elif cmd == 'compare':
		for l in comparePerformanceFiles(paths, sortby=sortby).strip().split('\n'):
			sys.stderr.write(l+'\n') # need to keep separate for coloring to work
	else:
		assert False


if __name__ == "__main__":
	_perfReporterMain(sys.argv[1:])

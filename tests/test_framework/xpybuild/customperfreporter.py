from pysys.utils.perfreporter import *
from pysys.constants import PROJECT
import logging, io, sys

def getXpybuildVersion(project):
	assert project, 'not initialized yet'
	with io.open(project.XPYBUILD_ROOT+'/release.properties', encoding='iso-8859-1') as f:
		key, version = f.read().strip().split('=')
		assert key=='VERSION', key
		return version


class XpybuildPerfReporter(CSVPerformanceReporter):
	def __init__(self, project, summaryfile, testoutdir):
		self.XPYBUILD_VERSION = getXpybuildVersion(project)

		super(XpybuildPerfReporter, self).__init__(project, summaryfile or 'performance_output/v'+self.XPYBUILD_VERSION+'/@OUTDIR@_@HOSTNAME@/perf_@DATE@_@TIME@.csv', testoutdir)
		self.unitAliases['ns'] = PerformanceUnit('ns', biggerIsBetter=False)
	
	def getRunDetails(self):
		d = super(XpybuildPerfReporter, self).getRunDetails()
			
		d['xpybuildVersion'] = self.XPYBUILD_VERSION
		d['platform'] = sys.platform
		return d

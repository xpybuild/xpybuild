from pysys.constants import *
from xpybuild.xpybuild_basetest import XpybuildBaseTest
import io

def getOpName(op):
	return op[:op.find('(')]

class PySysTest(XpybuildBaseTest):
	OPS = [
	'isDirPath(OUTPUT_DIR)', 'fileutils_isDirPath(OUTPUT_DIR)',
	'isWindows()', """normpath(OUTPUT_DIR+'/'+str(ops))""", """normLongPath(OUTPUT_DIR+'/'+str(ops))""", 
	'BuildFileLocation()',
	"""utils.fileutils.exists(OUTPUT_DIR+'/doesntexist')""",
	]


	def execute(self):
		for op in self.OPS:
			opname = getOpName(op)
			bf = self.output+'/'+opname+'.xpybuild.py'
			with io.open(self.input+'/test.xpybuild.py') as f:
				contents = f.read()
			with io.open(bf, 'w') as f:
				f.write(contents.replace('@OP@', op))
			self.xpybuild(buildfile=bf, shouldFail=False, args=['-n'],stdouterr=opname)

	def validate(self):
		for op in self.OPS:
			opname = getOpName(op)
			self.reportPerformanceResult(float(self.getExprFromFile(opname+'.out', 'Microbenchmark operation took ([0-9.]+) ms each')), 
				'Time per call to %s'%opname, 'ms')
			
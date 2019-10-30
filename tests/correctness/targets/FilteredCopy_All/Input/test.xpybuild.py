#
# Copyright (c) 2013 - 2017, 2019 Software AG, Darmstadt, Germany and/or its licensors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import os
import copy
from propertysupport import *
from buildcommon import *
from pathsets import *

# this is a convenient place to check we can use both with an without xpybuild.* qualification
from targets.copy import *
from xpybuild.targets.writefile import *

defineStringProperty('MY_PROP', 'prop_value')

WriteFile('${OUTPUT_DIR}/repl.txt', 'REPLACEMENT_FILE')

WriteFile('${OUTPUT_DIR}/test.txt', lambda context: """
Hello world
To be omitted
A line containing string replacement: stringreplace+old.
A line containing string replacement with no expansion: stringreplaceprop noexp ${MY_PROP}.
A line containing string replacement with expansion:    stringreplaceprop exp prop_value.
A line containing regex replacement with expansion: regex exp value.
A line containing regex replacement with no expansion: regex noexp value.
A line containing file contents replacement: filereplacement.
A line containing dict replacement: @replacedictkey@.

""")
Copy('${OUTPUT_DIR}/test2.txt', '${OUTPUT_DIR}/test.txt')


class InsertDestFileMapper(FileContentsMapper):
	def getInstance(self): 
		return copy.copy(self)
	def startFile(self, context, src, dest):
		assert os.sep in src, src
		assert os.sep in dest, dest
		assert os.path.abspath(src), src
		assert os.path.abspath(dest), dest

		self.currentfile = os.path.basename(src)
		if src.endswith('test2.txt'): return False # this mapper won't operate on this file
	def mapLine(self, context, line): return line
	def getHeader(self, context): 
		return 'InsertDestFileMapper: current source file is %s'%self.currentfile+os.linesep
	def getDescription(self, context): return 'InsertDestFileMapper()'
		

FilteredCopy('${OUTPUT_DIR}/copy-dest/', [
		'${OUTPUT_DIR}/test.txt', 
		'${OUTPUT_DIR}/test2.txt', 
	], 
	
	OmitLines('be.omitted'),
	StringReplaceLineMapper('stringreplace+old', 'stringreplace+new'),
	StringReplaceLineMapper('stringreplaceprop noexp ${MY_PROP}', 'replaced ${MY_PROP} no expansion', disablePropertyExpansion=True),
	StringReplaceLineMapper('stringreplaceprop exp ${MY_PROP}', 'replaced ${MY_PROP} with expansion'),
	RegexLineMapper('regex *exp value', 'regex replacement ${MY_PROP}'),
	RegexLineMapper('regex *noexp value', 'regex replacement ${MY_PROP}', disablePropertyExpansion=True),
	InsertFileContentsLineMapper('filereplacement', '${OUTPUT_DIR}/repl.txt'),
	createReplaceDictLineMappers({'replacedictkey':'replacedictvalue'}),

	InsertDestFileMapper(),
	AddFileHeader('File header with replacement ${MY_PROP}.'+os.linesep),
	AddFileHeader('File header without replacement ${MY_PROP}.'+os.linesep, disablePropertyExpansion=True),

	AddFileFooter('File footer with replacement ${MY_PROP}.'+os.linesep),
	AddFileFooter('File footer without replacement ${MY_PROP}.'+os.linesep, disablePropertyExpansion=True),
	)


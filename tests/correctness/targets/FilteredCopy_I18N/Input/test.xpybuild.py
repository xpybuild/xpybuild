#
# Copyright (c) 2019 Software AG, Darmstadt, Germany and/or its licensors
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
import codecs
from propertysupport import *
from buildcommon import *
from pathsets import *

from targets.copy import *
from targets.writefile import *

I18N = chr(163) # pound sign

defineStringProperty('Y', 'y')

WriteFile('${OUTPUT_DIR}/writefile-default.${Y}aml', f'Text is: {I18N}') # utf-8 is the default for .yaml files
WriteFile('${OUTPUT_DIR}/writefile-customized.foo.yaml', f'Text is: {I18N}').option('fileEncodingDecider', 
	ExtensionBasedFileEncodingDecider({'.foo.yaml':'iso-8859-1'}, 'ascii'))
WriteFile('${OUTPUT_DIR}/writefile-binary.bin', f'Text is: {I18N}'.encode('utf-8'))
WriteFile('${OUTPUT_DIR}/writefile-compressed.jpg', codecs.encode(f'Text is: {I18N}'.encode('utf-8'), 'bz2_codec'))


FilteredCopy('${OUTPUT_DIR}/copy-default.json', '${OUTPUT_DIR}/writefile-default.yaml', [StringReplaceLineMapper('Text', 'Replaced text'),]).option('fileEncodingDecider',
	ExtensionBasedFileEncodingDecider({'.doesnotmatchanything':'foo'}, None)) # invokes the default (global) value
FilteredCopy('${OUTPUT_DIR}/copy-customized.json', '${OUTPUT_DIR}/writefile-customized.foo.yaml', [StringReplaceLineMapper('Text', 'Replaced text'),]).option('fileEncodingDecider',
	ExtensionBasedFileEncodingDecider({'.${Y}aml':'iso-8859-1','.json':'iso-8859-1'}, None))

FilteredCopy('${OUTPUT_DIR}/copy-compressed.jpg', '${OUTPUT_DIR}/writefile-compressed.jpg') # rely on mime types to detect this as binary
# Definitions for options used by multiple targets

from propertysupport import defineOption, ExtensionBasedFileEncodingDecider
defineOption('fileEncodingDecider', ExtensionBasedFileEncodingDecider({
	'.json':'utf-8',
	'.xml':'utf-8',
	'.yaml':'utf-8', '.yml':'utf-8',
}, default='ascii'))

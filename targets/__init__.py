# Definitions for options used by multiple targets

from propertysupport import defineOption, ExtensionBasedFileEncodingDecider

defineOption('fileEncodingDecider', ExtensionBasedFileEncodingDecider.getDefaultFileEncodingDecider())

# Definitions for common options used by multiple targets

from propertysupport import defineOption, ExtensionBasedFileEncodingDecider

defineOption('common.fileEncodingDecider', ExtensionBasedFileEncodingDecider.getDefaultFileEncodingDecider())

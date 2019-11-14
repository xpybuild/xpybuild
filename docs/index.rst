.. xpybuild documentation master file, created by
   sphinx-quickstart on Wed Oct 23 18:53:21 2019.

Welcome to xpybuild
-------------------
Xpybuild is a fast cross-platform, cross-language build system that uses Python as the build file format. 

It supports Windows and Linux, uses build scripts written in Python 3.6+, and has built-in targets for Java, C/C++ and 
C# compilation, and for packaging/distribution operations like file copy/filtering and creating and unpacking 
.zip and .tar.gz archives. 

Why another build system? Simply put, while there's plenty to love about popular build tools such as Make, Ant, Maven, 
Gradle and SCons, they all have their blind spots, and we wanted to create something that combined the best bits of each. 

Xpybuild exists because we value:

	- *fast*, highly parallel builds that scale well, and deliver incremental/no-op builds really fast. For example, a large 
	  project with 2000+ highly complex C++, C#, Java and packaging output targets can check all dependencies to determine 
	  whether any incremental rebuilding is required in 2-4 seconds on a typical desktop machine. Many build systems 
	  just don't scale once you get into the 100s and 1000s of targets, 
	  leaving busy developers twiddling their thumbs throughout the day. 
	
	- *simple* build files that don't overcomplicate basic tasks. Building a basic Java .jar or C++ executable should 
	  be just a few simple lines of build script, and not require the build file author to burn time 
	  re-implementing potentially error-prone logic for standard operations like cleaning or up-to-dateness checking. 
	
	- *cross-platform* builds without the headaches. Any build system that relies on shell commands (e.g. Make) is always 
	  going to be prone to subtle behaviour differences between Unix-style systems and Windows; using Python abstracts 
	  away almost all such differences making it easy to create scripts that work everywhere.
	  
	- *clear error messages*, and 'fail-fast' instead of 'silently wrong' behaviour. There's nothing worse than a build script 
	  that generates different/wrong output to what's expected due to a minor 
	  typo in a file path or command line argument. Xpybuild is deliberately intolerant of mistakes such as commands 
	  that actually do nothing due to lack of matching input, and never swallow errors (though you can explicitly 
	  specify --keep-going when you need to). 
	  
	  It also includes a pluggable mechanism for parsing error/warning messages 
	  from different compilers and reformatting them for common IDEs and CI providers such as Visual Studio and 
	  Teamcity, and includes the build script location in all errors. The icing on the cake is that since everything 
	  is written in Python all stack traces are in user-editable Python text files (not hidden away in a Java class) 
	  so it's easy to add debugging code if you ever need to. 
	  
Sample build script
-------------------

Here's a sample build script that shows how easy it is to do some non-trivial compilation and packaging operations 
using xpybuild. Note how the build script specifies what is to be built but the framework takes care of up-to-dateness 
and cleaning without any extra logic in the build script::

	from xpybuild.propertysupport import *
	from xpybuild.buildcommon import *
	from xpybuild.pathsets import *

	from xpybuild.targets.java import *
	from xpybuild.targets.copy import *
	from xpybuild.targets.archive import *

	# xpybuild properties are immutable substitution values 
	# which can be overridden on the command line if needed
	# (property type can be a string/path/outputdir/list/enumeration/bool)
	defineStringProperty('APP_VERSION', '1.0.0.0')
	defineOutputDirProperty('OUTPUT_DIR', 'build-output')
	definePathProperty('MY_DEPENDENT_LIBRARY_DIR', './libs', mustExist=True)

	Jar('${OUTPUT_DIR}/myapp.jar', 
		# FindPaths walks a directory tree, supporting complex ant-style globbing patterns for include/exclude
		compile=[
			FindPaths('./src/', excludes=['**/VersionConstants.java']), 
			'${BUILD_WORK_DIR}/filtered-java-src/VersionConstants.java',
		],
		
		# DirBasedPathSet statically lists dependent paths under a directory
		classpath=[DirBasedPathSet('${MY_DEPENDENT_LIBRARY_DIR}/', 'mydep-api.jar', 'mydep-core.jar')],
		
		# Specify Jar-specific key/values for the MANIFEST.MF (in addition to any set globally via options)
		manifest={'Implementation-Title':'My Amazing Java Application'}, 
	).tags('myapp') # tags make it easy to build a subset of targets on the command line

	FilteredCopy('${BUILD_WORK_DIR}/filtered-java-src/VersionConstants.java', './src/VersionConstants.java', 
		StringReplaceLineMapper('@APP_VERSION@', '${APP_VERSION}'),
	)

	# Global 'options' provide an easy way to apply common settings to all targets; 
	# options can be overridden for individual targets using `BaseTarget.option(key,value)`
	setGlobalOption('jar.manifest.defaults', {'Implementation-Version': '${APP_VERSION}'})

	Zip('${OUTPUT_DIR}/myapp-${APP_VERSION}.zip', [
		'${OUTPUT_DIR}/myapp.jar',
		
		# The xpybuild "PathSet" concept provides a powerful way to specify sets of source paths, 
		# and to map each to a corresponding destination (in this case by adding on a prefix)
		AddDestPrefix('licenses/', FindPaths('./license-files/', includes='**/*.txt'))
	])

	# In a large build, you'd split your build across multiple files, included like this:
	include('subdir/otherbits.xpybuild.py')

This example shows the Jar, FilteredCopy and Zip targets, but explore the `xpybuild.targets` package to see C/C++ and
C# support, and see what else is available. The `xpybuild.pathsets` module explains more about the powerful "PathSet" 
concept that powers xpybuild's dependency and up-to-dateness checking. See `xpybuild.propertysupport` for more about 
properties and options. 

We hope you love using xpybuild!

Download
--------

Download the latest release of xpybuild from GitHub: https://github.com/xpybuild/xpybuild/releases

API documentation
-----------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   autodocgen/xpybuild.rst
   changelog.rst

License
-------
Copyright (c) 2013-2019 Ben Spiller and Matthew Johnson

Copyright (c) 2013-2019 Software AG, Darmstadt, Germany and/or its licensors

Licensed under the Apache License, Version 2.0 - see http://www.apache.org/licenses/LICENSE-2.0



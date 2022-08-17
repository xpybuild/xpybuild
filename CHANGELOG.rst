4.1 - UNDER DEVELOPMENT
=======================

Fixes
-----

- Fixed bug where errors logged during the "clean" phase between failure retries would be logged at ERROR potentially 
  causing the whole build to appear failed to CI/orchestration environments that check for errors. 
- Fixed `xpybuild.pathsets.FindPaths` and `xpybuild.pathsets.DirBasedPathSet` to be able to accept a target as its 
  first parameter. 
- Fixed the non-default console formatters (e.g. ``-F teamcity``) to print the full message including exception stack 
  traces, without which it is often hard to debug build failures. 
- Fixed the logging of the resolved paths to targets when doing a build with a small number (<20) of targets. 

Enhancements
------------

- Added support for ``.tar.xz`` archives to `xpybuild.targets.archive.Unpack`. 
- Added `xpybuild.utils.outputhandler.ProcessOutputHandler.Options.downgradeErrorsToWarnings` option for errors that 
  should be logged but not as errors - since error level log messages can be treated as fatal errors by some 
  CI/orchestration environments even if the job succeeds. 
- Added support for reading by filename (rather than just by file handle) and ``asDict`` argument to 
  `xpybuild.utils.fileutils.parsePropertiesFiles`. 

4.0
===

.. py:currentmodule:: xpybuild

Breaking changes
----------------

Removed support for Python 3.6, now the minimum version is Python 3.7+. 

Minor breaking changes in this release:

- Target paths can no longer contain filename characters which are prohibited on Windows such as ``<>:"|?*``. 
  This applies on all operating systems. 
- The special name ``full`` is now used instead of ``all`` to indicate the default set of targets (minus any 
  excluded using ``disableInFullBuild``). On the command line it is still permitted to specify ``all`` for 
  compatibility purposes but it is recommended to switch to ``full`` when possible. 
- Fixed `xpybuild.propertysupport.ExtensionBasedFileEncodingDecider` to match extensions case insensitively. 

Enhancements
------------

- Added support for Python 3.10. 
- Added a ``--search`` / ``-s`` command line option for locating targets/tags/properties/options. The search string 
  can be a substring match or a regular expression. This is a very convenient way to find out where in the build 
  something is defined. It is recommended to use this instead of the less powerful ``--target-info`` and 
  ``--find-target`` options in previous xpybuild releases. 
- Added a new ``FindPaths`` option `pathsets.FindPaths.Options.globalExcludesFunction` which can be used to globally exclude 
  certain file patterns throughout the build. By default this excludes files matching ``.nfs*`` (i.e. temporary NFS 
  files).
- Added more powerful "conditions" to `propertysupport.definePropertiesFromFile`, allowing for complex Python 
  expressions that check multiple conditions and properties to be used for dynamically selecting which lines are read 
  from ``.properties`` files. 
- Added `basetarget.BaseTarget.Options.failureRetries` option for easily retrying (with backoff) targets which can fail 
  transiently, e.g. due to flaky servers or interactions with anti-virus software that are outside your control. Like 
  any option, this can be set either per-target or globally (perhaps through a property) to increase the reliability of 
  automated build jobs. 
- Added `buildcommon.registerBuildLoadPostProcessor` to allow adding tags and options across all targets matching a 
  user defined criteria (e.g. targets of a particular Python class or containing a substring) just after all build 
  files have been loaded. 
- `propertysupport.defineOption` now returns a `propertysupport.Option` instance which provides a convenient way to 
  document your target options. See `basetarget.BaseTarget.Options` for an example of how this looks. 
- The log lines for each target are now buffered so they can be displayed consecutively in the ``.log`` file 
  (just as they already are on stdout) in a multi-threaded build. Note that this does not include the initial 
  ```*** Building targetname``` line (which is emitted as soon as the target begins, to help with debugging hanging 
  builds) but does include the final ```***``` line that indicates whether the target was successful, as well as all 
  intermediate log lines. 
- Property definition methods such as `propertysupport.definePathProperty` now return the (resolved) property value, 
  to avoid the need to call ``getPropertyValue`` when the value is directly needed in the build file. 
- Added a ``commands=`` argument to `xpybuild.targets.custom.CustomCommand` 
  (and `xpybuild.targets.custom.CustomCommandWithCopy`) which allows an output directory to be created by 
  executing a sequence of multiple commands rather than needing separate targets for each command. 
- Improved log messages when `xpybuild.targets.custom.CustomCommand` fails, to provide more information about 
  the output of the failed process. 
- Added common archive formats such as ``.zip`` and ``.jar`` to the default 
  `xpybuild.propertysupport.ExtensionBasedFileEncodingDecider`. 

Fixes
-----

- Fixed a possible AssertionError race condition when executing a ``--rebuild`` with targets whose path changes 
  between the clean and build phases (for example, due to containing a timestamp or random number). 
- Fixed the ``javac.target`` option to do the correct thing (was previously setting ``-source`` not ``-target`` (GH-6). 

NB: There was a re-release of 4.0 on 2022-01-27 shortly after the initial release to fix a couple of minor issues.

3.0
===

Breaking changes
----------------

-  Now requires Python 3.6+ instead of Python 2
-  Added ``output`` and ``buildOptions`` required arguments to the 
   `ConsoleFormatter` base class constructor.
- `xpybuild.targets.copy.FilteredCopy` and `xpybuild.targets.writefile.WriteFile` now use the option 
  ``common.fileEncodingDecider`` to select which encoding to use for character transformations instead of defaulting 
  to whatever the local default encoding is. You may need to provide a custom 
  `xpybuild.propertysupport.ExtensionBasedFileEncodingDecider` instance if you are 
  filtering text files with unusual extensions::
  
		setGlobalOption("common.fileEncodingDecider", ExtensionBasedFileEncodingDecider({
			'.foo': 'utf-8', 
			'.bar': ExtensionBasedFileEncodingDecider.BINARY,
			}, default=ExtensionBasedFileEncodingDecider.getDefaultFileEncodingDecider()))
				
-  Also note that FilteredCopy mappers and the WriteFile targets now 
   only map with unicode character ``str`` objects and not ``bytes``.
-  BuildContext.defaultOptions() was removed, as there is no legitimate
   use case for it.
-  ``tmpdir`` has been removed from the target's ``self.options``;
   instead if needed the target's ``self.workDir`` should be used
   explicitly.
-  Module names and contents have been re-organized in this release,
   which will require changes to build files in some cases:

   - All xpybuild modules have been moved to a new ``xpybuild.`` module
     for namespacing purposes. The `buildcommon.enableLegacyXpybuildModuleNames()`
     function can be called (after importing xpybuild.buildcommon)
     to allow unqualified access to the names if you have a large
     project, though this is a temporary measure and willbe removed
     eventually.
   - The xpybuild.py entry-point script is now one level above the
     directory for the ``xpybuild`` package.
   - The `xpybuild.main()` function (which some scripts may have
     directly referenced) is replaced by
     `xpybuild.__main__.main`.
   - The undocumented ``_XPYBUILD_VERSION`` constant was renamed to 
     `xpybuild.buildcommon.XPYBUILD_VERSION`. 
   - ``formatFileLocation`` was moved from ``buildcommon`` to 
     `xpybuild.utils.buildfilelocation.formatFileLocation`.
   - ``propertyfunctors`` contents have been moved into `xpybuild.propertysupport`, 
     except for ``make_functor`` which has moved to `xpybuild.utils.functors.makeFunctor`. 
   - ``buildexceptions`` module was moved to `xpybuild.utils.buildexceptions`; the 
     `buildcommon.enableLegacyXpybuildModuleNames()` function temporarily allows use of the old name. 
   - ``Touch`` target was moved from ``targets.touch`` to `xpybuild.targets.writefile.Touch`; the 
     `buildcommon.enableLegacyXpybuildModuleNames()` function temporarily allows use of the old name.
   - ``Unpack``, ``Zip`` and ``Tarball`` targets were moved to the `xpybuild.targets.archive` 
     module; the `buildcommon.enableLegacyXpybuildModuleNames()` function temporarily allows use of the old name.
   - The console formatter modules ``teamcity``, ``visualstudio`` and ``make`` 
     have been deleted and their contents moved into `xpybuild.utils.consoleformatter`. 
   - The ``formatTimePeriod`` method was removed from ``timeutils`` and moved to 
     `xpybuild.utils.stringutils.formatTimePeriod`. 
   - The ``lowerCurrentProcessPriority()`` function was removed. 
   - ``buildcommon.getStdoutEncoding`` was removed, replaced by 
     `xpybuild.utils.process.defaultProcessOutputEncodingDecider` and the associated option. 

Deprecation
-----------
The following deprecated items are likely to be removed soon, so action is required 
if you're using them:

- ``buildcommon.normpath`` is deprecated and should not be used - switch to 
  `xpybuild.utils.fileutils.normLongPath` or `xpybuild.utils.fileutils.normPath` instead. 
- ``getBuildInitializationContext()`` is deprecated and replaced by 
  `xpybuild.buildcontext.BuildInitializationContext.getBuildInitializationContext()`.
- ``propertysupport.getProperty`` is deprecated in favour of 
  `xpybuild.propertysupport.getPropertyValue`. 
- `xpybuild.utils.fileutils` methods ``getstat``, ``getmtime``, ``getsize``, 
  ``exists``, ``isfile``, ``isdir`` have been renamed to ``cached_XXX`` 
  to better indicate the semantics. The old names are deprecated. 
- ``xpybuild.targets.basetarget.targetNameToUniqueId`` is replaced by 
  `xpybuild.targets.basetarget.BaseTarget.targetNameToUniqueId`. 
- ``xpybuild.basetarget.BaseTarget.addHashableImplicitInput/Option`` is replaced by 
  `xpybuild.basetarget.BaseTarget.registerImplicitInput` and 
  `xpybuild.basetarget.BaseTarget.registerImplicitInputOption`. 

See also the module re-organization listed under breaking changes; all xpybuild 
modules and classes should now be accessed via their new names, typically 
starting ``xpybuild.` (e.g. ``xpybuild.targets.copy`` etc).

The following have also been deprecated: 
 
- The ``isWindows()`` function is deprecated in favour of the `xpybuild.buildcommon.IS_WINDOWS` 
  constant (which is faster).
- ``BuildContext.mergeOptions()`` is deprecated in favour of
  `xpybuild.basetarget.BaseTarget.options`, or (for situations where there is no target such
  as PathSets) `xpybuild.buildcontext.BuildContext.getGlobalOption()`.


Fixes
-----

-  Fixed a couple of bugs in incremental C++ compilation - one that
   could cause unnecessary incremental compilation of targets that
   depend on generated C/C++ source or include files, and another in
   which the build would fail rather than re-running makedepends if some
   of the cached dependencies no longer exist.

Enhancements
------------

-  Command line now accepts a new option ``--rebuild-ignore-deps`` or ``--rid`` which is equivalent to 
   ``--rebuild --ignore-deps`` and produces a quick way to force a rebuild of a few targets/tags without any of their 
   dependencies getting rebuilt. 
-  `xpybuild.targets.copy.FilteredCopy`, `xpybuild.targets.writefile.WriteFile`: Added 
   option ``common.fileEncodingDecider``
   which is used by FilteredCopy and WriteFile to decide what encoding
   to use for reading/writing text files. The default is an
   `xpybuild.propertysupport.ExtensionBasedFileEncodingDecider` instance 
   which specifies UTF-8 for
   yaml/json/xml files, binary for some common binary types such as
   images, and 'ascii' for everything else - which means an exception
   will be thrown if any files containing characters outside the 7-bit
   ASCII range are present. Alternative encodings such as utf-8 can be
   specified for a given file extension, globally or on a per-target
   basis.
-  `xpybuild.targets.writefile.WriteFile`: added ``encoding=`` option to WriteFile
   (``common.fileEncodingDecider`` option is used if not specified).
-  `xpybuild.targets.writefile.WriteFile`: added support for writing binary bytes.
-  `xpybuild.basetarget.BaseTarget`: Added ``BaseTarget.openFile`` which should be used for
   opening files (especially text files) from targets. It automatically
   picks the correct encoding to use for text files using the
   ``common.fileEncodingDecider`` option. This uses the ``openForWrite``
   method which can now be used to write unicode strings in text mode,
   not only binary bytes. The available options are now pretty similar
   to what ``io.open`` supports, and ``openForWrite`` should be used
   instead of io.open/open to avoid possible file system races on
   Windows.
-  `basetarget.BaseTarget.addImplicitInput`: added ability to pass a callable 
   that returns a list of items, so there's no longer anything that only 
   ``getHashableImplicitInputs()`` can do. 
-  `BaseTarget.addImplicitInputOption`: added ability to pass a 
   lambda that dynamically selects which of the defined options to include, 
   for example based on prefix matching. 
-  `xpybuild.targets.custom.CustomCommand`: now supports customized handling 
   of process output and return code using the new 
   ``CustomCommand.outputHandlerFactory`` option. 
-  Added ``utils.stringutils.compareVersions`` method for comparing
   dotted version strings.

1.15
====

Breaking changes
----------------

-  Native C/C++ targets now treat include directories as dependencies,
   which means that the set of targets they depend on can (and must) be
   known before the build begins (i.e. without running makedepend). All
   include directories must now either be statically available before
   the build starts, or themselves be a directory target. For advanced
   cases where you need to specify an include directory that is not
   itself a target but is made up of a set of file or directory targets,
   use TargetsWithinDir.
-  PathSet class no longer exists, replaced by a function of the same
   name that creates a new instance only if needed. If you have code
   that subclasses PathSet change it to subclass BasePathSet.
-  ``BasePathSet._resolveUnderlyingDepenencies()`` now returns a generator
   of (path, pathset) instead of a list of [path]. This only affects
   users with a custom subclass of BasePathSet with an override of this
   method (and does not affect you if you used DerivedPathSet).
-  Target priority can no longer be set to a negative number; 0.0 is the
   minimum.
-  The native C target was previously using the C++
   (``native.cxx.flags``) compiler options during dependency generation
   ratehr than ``native.c.flags``; this is now fixed but it may be
   necessary to add additional flags explicitly if you have C targets
   that are relying on them.
-  The build now runs in parallel by default (equivalent to -J); if you
   need single-threaded execution, use the command line parameter
   ``-j1``.

Deprecation
-----------

-  Support for specifying C/C++ include directories without a trailing
   slash (as is normal in xpybuild) is now discouraged and may be
   removed in a future release.

Fixes
-----

-  Native C/C++ compilation dependency checking has been rewritten to
   fix a number of correctness and performance problems in both full and
   incremental builds, especially around handling of include directories
   and source files generated by another target.
-  Jar: manifest creation (``create_manifest``) was in some cases
   generating invalid manifest.mf files if whitespace in values happened
   to be near the newline position. This is corrected, leading/trailing
   whitespace is stripped from keys and values automatically, non-ASCII
   (I18N) characters are correctly encoded to UTF-8, and (for
   simplicity) \\n newlines are now used regardless of the local OS
   default.
-  Javac: to avoid unwanted failures, stdout outpuot is no logner used
   for warnings/errors, and also when the return code is 0 (success) any
   stderr output is treated as warnings not errors regardless of its
   content. Does not affect ``javac.warningsAsErrors`` is implemented by
   javac itself.

Enhancements
------------

-  Pathsets: A new pathset called `xpybuild.pathsets.TargetsWithinDir` has been added. This
   is similar to `xpybuild.pathsets.TargetsWithTag` but uses just a parent directory name to
   locate associated targets, and can be used as a parameter to
   FindPaths if you need to copy files generated by all targets under
   the specified directory.
-  A new check has been added that will cause a build failure if any
   target is depending on a file (located under the output directory)
   that is generated by a directory target but without using
   DirGeneratedByTarget. This is a subtle but common cause of race
   conditions due to incorrect dependency information, and it should now
   be more obvious if such a problem exists.
-  basetarget: new utility methods have been added
   addHashableImplicitInputOption('optionkey') and
   addHashableImplicitInput('foo=bar') to make it easier for target
   classes to specify their implicit inputs without needing to implement
   getHashableImplicitInputs()
-  buildcontext: getExpandPropertyValues() now handles callable(context)
   inputs as well as other strings, allowing it to perform common
   resolutions needed in many different situations.
-  Command line: new (experimental) option --verify that can be used to
   run the build in a slower and stricter mode that will flag up
   potential build problems. This feature should be considered
   experimental in this release.
-  Javac: now respects the ``ProcessOutputHandler.regexIgnore`` option.
-  Copy: added ``Copy.symlinks`` option which can be used to enable
   copying of symlinks. To turn this on globally for your build, use
   ``setGlobalOption('Copy.symlinks', True)``.
-  FilteredCopy: added disablePropertyExpansion to
   AddFileHeader/AddFileFooter/RegexLineMapper
-  FilteredCopy: added FileContentsMapper.startFile(context, src, dest)
   API method that can be used to skip use of this mapper for certain
   files, and/or to insert content based on the source or destination
   path into the file.
-  FilteredCopy: added FileContentsMapper.prepare(context) API method
   that can be used to prepare fields based on the context to speed up
   the actual mapping.
-  Cpp/C native targets: added
   ``native.include.upToDateCheckIgnoreRegex`` and
   ``native.include.upToDateCheckIgnoreSystemHeaders`` options which can
   be used to speed up up-to-date checking by excluding large include
   directories that never change.
-  The build now runs in parallel by default (no need to use the ``-J``
   option). Additionally, the default number of workers can now be
   specified in the build file, as an integer or float, e.g.::

      import multiprocessing
      setGlobalOption('build.workers', multiprocessing.cpu_count() * 0.75)

   The default value for this option is one worker per CPU. The maximum
   number of workers can be limited on a per-machine/user basis using
   the ``XPYBUILD_WORKERS_PER_CPU`` and/or ``XPYBUILD_MAX_WORKERS``
   variables. The ``-j`` command line option can still be used to
   explicitly override the number of workers (taking precedence over all
   other settings), for example use ``-j1`` for a single-threaded build.

1.14
====

Breaking changes
----------------

-  FindPaths/anGlob: Add constraint that \*\*/\*/ patterns are no longer
   permitted; this construct is not very useful in practice and
   supporting it would hurt performance considerably.

Deprecation
-----------

None

Fixes
-----

-  "Unknown option tmpdir" regression introduced 1.13 when calling
   mergeOptions(options=self.options) is now fixed; though it's
   recommended to just use self.options and avoid mergeOptions now.
-  CustomCommand was only passing environment variables from the parent
   process/shell to the new process when env overrides were specified
   but not when an empty env dictionary was specified. Now these are
   passed in all cases.

Enhancements
------------

-  Significant performance improvement to depending checking phase
   (fixing a regression introduced in 1.13, plus additional
   improvements), and to FindPaths and antGlob, especially when matching
   a large number of patterns within a single directory.
-  IS\_WINDOWS: new constant, replaces the isWindows() function and is
   significantly faster to use.
-  fileutils.toLongPathSafe: new method which implements Windows logic
   for allowing paths longer than 256 characters to be operated on. This
   is similar to normLongPath but does not perform
   canonicalization/normalization so is a lot faster for cases where
   that is not required.
-  StringReplaceLineMapper now has an optional parameter
   disablePropertyExpansion which can be used to disable ${...}
   expansion
-  Improved usability of --profile option, which now generates textual
   output, aggregates across all threads, and includes profiling for the
   build file parsing phase
-  Improve dependency checking performance
-  Javadoc now has an option "javadoc.ignoreSourceFilesFromClasspath"
   which can be enabled to prevent .java files in classpath jars from
   being parsed (by setting an empty directory for the -sourcepath),
   which can lead to errors if classpath jars contain source that
   requires optional dependencies which are not present.
-  ProcessOutputHandler: new option regexIgnore can be set to a string
   which will be ignored by the output handler. This can be used to
   suppress unwanted logging, and to selectively ignore warning and
   error lines.
-  ProcessOutputHandler: new option ignoreReturnCode can be set to
   prevent a non-zero return code from being treated as an error.
-  ProcessOutputHandler: new option factory can be set to specify a
   function or class to be used instead of ProcessOutputHandler for
   output of a specific target, allowing detailed customization of
   behaviour. The new static function ProcessOutputHandler.create(...,
   options) should be used instead of the ProcessOutputHandler handler
   to ensure that this option is honoured if set.
-  javac/visualstudio/csharp/docker: all have a new outputHandlerFactory
   option which can be set to override the default ProcessOutputHandler
   subclass used for these targets, for example to customize handling of
   errors and warnings.
-  process.call(): this method now accepts an options dictionary, which
   should be set wherever possible; this avoids callers having to deal
   with passing boilerplate defaults in to call manually.

1.13
====

Breaking changes
----------------

-  It is now an error to use a relative path in a PathSet that is
   instantiated after the end of the parsing phase (e.g. while building
   or dependency checking a target) or from a python "import" statement.
   This is because it is impossible to guarantee a correct location can
   be found and better to fail early and clearly than in a subtle way.
   Either ensure PathSets are instantiated as top-level items in build
   files referenced from an include(...) statement, or use an absolute
   path if this is not possible.
-  normLongPath now returns paths including a trailing slash if the
   input contains a trailing slash (indicating a directory), whereas
   before the trailing slash would be stripped off. The provides
   consistency with normpath.

Deprecation
-----------

-  Assigning to self.options (e.g. from a target's constructor) is
   deprecated; it will continue to be permitted for now, but due to
   various edge cases this pattern is strongly discouraged. Best
   practice is to call .option(...) on the target after the constructor
   has returned to specify any target-specific options.

Breaking changes
----------------

-  The semantics of reading self.options from a target have changed in
   order to fix some edge cases and provide better usability. Previously
   reading self.options was permitted at any point in the build
   lifecycle but would usually return unresolved target-specific
   overrides and sometimes inconsistent results. Now reading
   self.options will return a dictionary containing fully resolved
   options in force for this target, including global option values and
   target-specific overrides. It is no longer permitted to read the
   self.options from a target's constructor i.e. during the build
   initialization phase (as the resolved option values are not yet
   available); this will now produce an exception.

Fixes
-----

-  A target or tag that is disabled in the full build will now be
   included in the build if specified explicitly even when "all" is also
   specified in the same invocation of xpybuild.py
-  Target options specified using .options(...) were being applied on a
   per-class basis, leading to the options set on the final target of a
   given class taking effect for all targets of that class. This is now
   fixed.

Enhancements
------------

-  Options framework: a target-specific dictionary of resovled options
   is now available directly from basetarget.options so there is no
   longer any need to use buildcontext.mergeOptions. There is also a new
   method basetarget.getOption() for getting an option value with
   automatic checking for None/empty string values.
-  Cpp/C: Improve clarity of error messages from C/C++ dependency
   checking by including the source file in the message (if there is
   only one - which is the common case)
-  FilteredCopy: permit an empty list of mappers to make it easier to
   specify replacements that only apply to one platform (e.g. line
   endings), add best practice info in target doc and add
   allowUnusedMappers property for when all else fails
-  Improve build file location and exception handling: only attach build
   file location information to an exception if it is obtained during
   the parsing phase, and only from the include(...) file currently
   being processed, to avoid unuseful locations from common utility
   classes. Except for where an error results from an item with its own
   location such as a PathSet, set location to None and use the location
   of the target being built/dependency-checked. Allow including both
   location (e.g. from a pathset) and target name in an exception
   message if both are available.
-  Add ProcessOutputHandler.getLastOutputLine() method and use it to
   improve the default handleEnd() message if there is a non-zero error
   code but no errors or warnings
-  Include regualar progress messages during dependency resolution, and
   log a message when starting each build phase
-  Add PySys-based framework for proper automated testing of xpybuild
-  PathSets, Jar: previously use of ".." in destination paths was
   disallowed by AddDestPrefix and most other mappers, now it is
   permitted which allows use of AddDestPrefix to add parent-relative
   paths to the classpath in .jar manifests. Targets that use the
   destinations to write to the local file system are required to check
   for and disallow ".." to avoid accidentally writing to locations
   outside their specified target directory.
-  Add Download target for retrieving HTTP/FTP URLs
-  Add DockerBuild and DockerTagUpload targets for building docker
   images and pushing them to repositories
-  BaseTarget: add updateStampFile() method for targets which use an
   artificial output file to maintain up-to-dateness

1.12
====

This is the first official public release of xpybuild

Breaking changes
----------------

-  Zip: Changed Zip target to fail with an error if duplicate entries
   are added to the zip, previously the target would create a zip with
   duplicate entries which would cause problems for some tools
-  functors: Moved internal.functors to utils.functors
-  teamcity.\ *publishArtifact: Deprecate teamcity.*\ publishArtifact
   and replace with a general-purpose BuildContext.publishArtifact
   method that can be handled in a custom way by each output formatter
-  utils.loghandler.LogHandler: Remove utils.loghandler.LogHandler to
   utils.consoleformatter.ConsoleFormatter (also renamed all known
   subclasses)

Deprecation
-----------

-  teamcity.\_publishArtifact: replaced with a general-purpose
   BuildContext.publishArtifact method

Fixes
-----

-  Jar: Jar generation now always uses platform-neutral / separators
   instead of OS-specific slashes in manifest.mf files, which is
   required for Java to read them correctly
-  CustomCommand: Publish stdout/err as artifacts even if large; also
   fix logic for deciding whether command succeeded or failed

Enhancements
------------

-  Jar: The jar.manifest.classpathAppend option now allows and ignores
   "None" items in the list
-  Cpp/C: Check for explicit dependencies before implicit dependencies,
   so we get error messages sooner
-  VisualStudioProcessOutputHandler: Added new options
   "visualstudio.transientErrorRegex" which allows certain errors (e.g.
   Access Denied) to be handled with a wait-and-retry rather than
   immediately failing
-  CSharp, SignJars, Javadoc, Cpp: Target options are now passed down to
   process output handlers to allow customizeable behaviour
-  CustomCommand: support full set of expansions including PathSets for
   environment variable values
-  CustomCommand: add CustomCommand.TARGET and DEPENDENCIES special
   values to avoid the need to duplicate information
-  All targets: Output handlers will include the first warning line in
   the target failure exception if there were no specified errors logged


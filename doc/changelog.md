# 1.13

## Breaking changes
- It is now an error to use a relative path in a PathSet that is instantiated after the end of the parsing phase (e.g. while building or dependency checking a target) or from a python "import" statement. This is because it is impossible to guarantee a correct location can be found and better to fail early and clearly than in a subtle way. Either ensure PathSets are instantiated as top-level items in build files referenced from an include(...) statement, or use an absolute path if this is not possible. 
- normLongPath now returns paths including a trailing slash if the input contains a trailing slash (indicating a directory), whereas before the trailing slash would be stripped off. The provides consistency with normpath. 

## Deprecation
- Assigning to self.options (e.g. from a target's constructor) is deprecated; it will continue to be permitted for now, but due to various edge cases this pattern is strongly discouraged. Best practice is to call .option(...) on the target after the constructor has returned to specify any target-specific options. 

## Breaking changes
- The semantics of reading self.options from a target have changed in order to fix some edge cases and provide better usability. Previously reading self.options was permitted at any point in the build lifecycle but would usually return unresolved target-specific overrides and sometimes inconsistent results. Now reading self.options will return a dictionary containing fully resolved options in force for this target, including global option values and target-specific overrides. It is no longer permitted to read the self.options from a target's constructor i.e. during the build initialization phase (as the resolved option values are not yet available); this will now produce an exception. 

## Fixes
- A target or tag that is disabled in the full build will now be included in the build if specified explicitly even when "all" is also specified in the same invocation of xpybuild.py
- Target options specified using .options(...) were being applied on a per-class basis, leading to the options set on the final target of a given class taking effect for all targets of that class. This is now fixed. 

## Enhancements
- Options framework: a target-specific dictionary of resovled options is now available directly from basetarget.options so there is no longer any need to use buildcontext.mergeOptions. There is also a new method basetarget.getOption() for getting an option value with automatic checking for None/empty string values. 
- Cpp/C: Improve clarity of error messages from C/C++ dependency checking by including the source file in the message (if there is only one - which is the common case)
- FilteredCopy: permit an empty list of mappers to make it easier to specify replacements that only apply to one platform (e.g. line endings), add best practice info in target doc and add allowUnusedMappers property for when all else fails
- Improve build file location and exception handling: only attach build file location information to an exception if it is obtained during the parsing phase, and only from the include(...) file currently being processed, to avoid unuseful locations from common utility classes. Except for where an error results from an item with its own location such as a PathSet, set location to None and use the location of the target being built/dependency-checked. Allow including both location (e.g. from a pathset) and target name in an exception message if both are available. 
- Add ProcessOutputHandler.getLastOutputLine() method and use it to improve the default handleEnd() message if there is a non-zero error code but no errors or warnings
- Include regualar progress messages during dependency resolution, and log a message when starting each build phase
- Add PySys-based framework for proper automated testing of xpybuild
- PathSets, Jar: previously use of ".." in destination paths was disallowed by AddDestPrefix and most other mappers, now it is permitted which allows use of AddDestPrefix to add parent-relative paths to the classpath in .jar manifests. Targets that use the destinations to write to the local file system are required to check for and disallow ".." to avoid accidentally writing to locations outside their specified target directory. 
- Add Download target for retrieving HTTP/FTP URLs
- Add DockerBuild and DockerTagUpload targets for building docker images and pushing them to repositories
- BaseTarget: add updateStampFile() method for targets which use an artificial output file to maintain up-to-dateness

# 1.12

This is the first official public release of xpybuild

## Breaking changes
- Zip: Changed Zip target to fail with an error if duplicate entries are added to the zip, previously the target would create a zip with duplicate entries which would cause problems for some tools
- functors: Moved internal.functors to utils.functors
- teamcity._publishArtifact: Deprecate teamcity._publishArtifact and replace with a general-purpose BuildContext.publishArtifact method that can be handled in a custom way by each output formatter
- utils.loghandler.LogHandler: Remove utils.loghandler.LogHandler to utils.consoleformatter.ConsoleFormatter (also renamed all known subclasses)

## Deprecation
- teamcity._publishArtifact: replaced with a general-purpose BuildContext.publishArtifact method

## Fixes
- Jar: Jar generation now always uses platform-neutral / separators instead of OS-specific slashes in manifest.mf files, which is required for Java to read them correctly
- CustomCommand: Publish stdout/err as artifacts even if large; also fix logic for deciding whether command succeeded or failed

## Enhancements
- Jar: The jar.manifest.classpathAppend option now allows and ignores "None" items in the list
- Cpp/C: Check for explicit dependencies before implicit dependencies, so we get error messages sooner
- VisualStudioProcessOutputHandler: Added new options "visualstudio.transientErrorRegex" which allows certain errors (e.g. Access Denied) to be handled with a wait-and-retry rather than immediately failing
- CSharp, SignJars, Javadoc, Cpp: Target options are now passed down to process output handlers to allow customizeable behaviour
- CustomCommand: support full set of expansions including PathSets for environment variable values
- CustomCommand: add CustomCommand.TARGET and DEPENDENCIES special values to avoid the need to duplicate information
- All targets: Output handlers will include the first warning line in the target failure exception if there were no specified errors logged

# 1.12

This is the first official public release of xpybuild

## Breaking changes
- Zip: Changed Zip target to fail with an error if duplicate entries are added to the zip, previously the target would create a zip with duplicate entries which would cause problems for some tools

## Fixes
- Jar: Jar generation now always uses platform-neutral / separators instead of OS-specific slashes in manifest.mf files, which is required for Java to read them correctly
- CustomCommand: Publish stdout/err as artifacts even if large

## Enhancements
- Jar: The jar.manifest.classpathAppend option now allows and ignores "None" items in the list
- Cpp/C: Check for explicit dependencies before implicit dependencies, so we get error messages sooner
- VisualStudioProcessOutputHandler: Added new options "visualstudio.transientErrorRegex" which allows certain errors (e.g. Access Denied) to be handled with a wait-and-retry rather than immediately failing
- CSharp, SignJars, Javadoc, Cpp: Target options are now passed down to process output handlers to allow customizeable behaviour
- CustomCommand: support full set of expansions including PathSets for environment variable values
- CustomCommand: add CustomCommand.TARGET and DEPENDENCIES special values to avoid the need to duplicate information
- All targets: Output handlers will include the first warning line in the target failure exception if there were no specified errors logged

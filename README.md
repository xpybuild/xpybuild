xpybuild
========
[![Build Status](https://travis-ci.com/xpybuild/xpybuild.svg?branch=master)](https://travis-ci.com/xpybuild/xpybuild)

XPyBuild is a cross-platform, cross-language, multi-threaded build system that uses Python as the build file format. 

It combines the best features of Make with those from Ant along with an easy to use but powerful blend of declarative statements and imperative python code.

XPyBuild requires Python 3.6+. 

The values behind this build system are:
   - correct build
   - fast, parallelisable, scalable build
   - simple build files, all complexities abstracted away in reusable helper 
       classes
   - fail-early on build configuration bugs (e.g. setting an unknown property)

Key concepts:
   - properties - immutable values specified by build files or overridden on 
       command line. May be path, a string, True/False or list. 
       Can be evaluated using "${propertyName}. All properties must be defined 
       in a build file before they can be used. 
   - target - something that generates an output file (or directory)
       if the output file doesn't exist or is out of date with respect to 
       other targets it depends on; has the ability to clean/delete any 
       generated output. 
       Targets are named based on their output file, but may also have 
       tags to make referring to them easier. 
   - tag - an alias for a target or set of targets, grouped together to make 
       running them easier from the command line
   - PathSet - an object that specifies a set of on-disk files/directories, 
       typically used as the source of targets (e.g. Copy) or to indicate 
       dependencies. PathSets can efficiently detect whether their source 
       files are up-to-date, and also have the ability to specify a 
       "destination" for each source path, which is used by targets such as 
       Copy. 

Links
=====
* [API Documentation](https://xpybuild.github.io/xpybuild/)
* [Change Log](https://github.com/xpybuild/xpybuild/blob/master/doc/changelog.md)

Copyright and license
=====================
Copyright (c) 2013-2019 Ben Spiller and Matthew Johnson
Copyright (c) 2013-2019 Software AG, Darmstadt, Germany and/or its licensors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

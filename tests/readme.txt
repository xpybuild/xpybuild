These tests are written using the opensource PySys test framework. 

Simply invoke "pysys run" from this directory (or any directory below it). 

Environment variables for controlling the tests:

- to enable automatic performance comparisons against previous baseline(s):
set PYSYS_PERFORMANCE_BASELINES=v1.12=c:\dev\xpybuild\tests\performance_output\v1.12,v1.13=c:\dev\xpybuild\tests\performance_output\v1.13,latest=c:\dev\xpybuild\tests\performance_output\*\latest*@latest 

- to enable per-line profiling using pprofile, if installed
set XPYBUILD_PPROFILE=<path to pprofile>\pprofile.py

- to enable coverage reporting:
pysys run -XpythonCoverage=true

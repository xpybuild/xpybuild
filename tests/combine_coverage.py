#!/usr/bin/env python2

""" Utility script that finds .coverage files under the current directory and combines them into a single file, deleting them as it goes.
"""

from __future__ import print_function
import time, sys, os.path
import coverage

def main(args):
	if args:
		print("Run this tool from the directory you wish to crawl for .coverage files. ")
		print("Has no arguments. Produces")
		return
	
	print("Searching for .coverage* files under %s"%os.path.normpath('.'))
	cov = []
	for (dirpath, dirnames, filenames) in os.walk('.'):
		for f in filenames:
			if f == '.coverage.combined': continue
			if f.startswith('.coverage'): cov.append(os.path.join(dirpath, f))
	
	if cov:
		print('Found %d coverage file(s)'%(len(cov)))
		dest = os.path.abspath('./.coverage.combined')
		c = coverage.Coverage(dest)
		# nb: combine automatically deletes all the files (!)
		c.combine(cov)
		c.save() 
		print('Saved combined coverage to: %s'%dest)
	else:
		print("Nothing to do - no coverage files found")
		
if __name__ == "__main__":
	main(sys.argv[1:])

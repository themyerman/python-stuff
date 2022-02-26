#!/usr/bin/python

import os.path
import re, sys
import getopt
from conf import rules


def main(argv):
	"""
	pull in config items for topdir
	or change from command line
	pull in file extension
	only scans folders that are set in scan_folder
	run os.walk() and determine
	which ruleset to use (specific/general)
	"""
	
	verbose = ''
	quick = ''
	folders = ''
	topdir = ''
	scan_levels = ''
	
	#let's not even go anywhere if there are no arguments passed in!
	if len(sys.argv) == 1:
		usage()
		sys.exit(2)
		
	try:
		"""
		args are:
			h, help
			i, ignore (must have arg)
			q, quick
			v, verbose
			t, topdir (must have arg)
			f, folders (must have arg)
			s, scan levels (must have arg)
		"""
		opts, args = getopt.getopt(argv,"hi:qvt:f:s:",["help=","ignore=","quick=","verbose=","topdir=""folders=","scan_levels="])
	except getopt.GetoptError:
		usage()
		sys.exit(2)
	
	
	print
	print '====================================================='
	print '==         EYE OF SAURON                           =='
	print '==                                                 =='
	print '==       "the eye sees all"                        =='
	print '====================================================='
	print

	for opt, arg in opts:
		if opt in ('-h', '--help'):
			usage()
			sys.exit()
		elif opt in ('-t', '--topdir'):
			rules['topdir'] = arg
			print '* TOPDIR now set to ' + rules['topdir']
		elif opt in ('-v' '--verbose'):
			rules['print_ok'] = True
			rules['scan_level'] = ['high','medium','low']
			verbose = True	
			quick = False	
		elif opt in ('-q', '--quick'):
			rules['print_ok'] = False
			rules['scan_level'] = ['high']
			verbose = False
			quick = True
		elif opt in ('-f', '--folders'):
			rules['scan_folders'] = arg.split(',')
			print '* SCANNING FOLDERS now set to ' + (', ').join(rules['scan_folders'])
		elif opt in ('-s', '--scan_levels'):
			rules['scan_level'] = arg.split(',')
			print '* SCANNING LEVELS now set to ' + (', ').join(rules['scan_level'])
		elif opt in ('-i', '--ignore'):
			rules['ignore'] = arg.split(',')
			print '* IGNORING these ' + (', ').join(rules['ignore'])
			
			
	if verbose:
		print "* VERBOSE mode"
	elif quick:
		print "* QUICK mode"
	
	print
	print '* STARTING SCAN'
	print
						
	for root,subs,files in os.walk(rules['topdir']):
		for scandir in rules['scan_folders']:
			if scandir not in root:
				continue
			
			for fname in files:
				short,ext = os.path.splitext(fname)
				if ext not in rules['extensions']:
					continue
									
				file_name = os.path.join(root,fname)
				if fname in rules['rule_set'][ext]['specific']:
					check_specific_rules(file_name,ext)
				else:
					check_generic_rules(file_name,ext)				
	print
	print '* COMPLETE'
	print

def check_specific_rules(file_name,ext):
	"""
	check_specific_rules --- loads rules for filename
	and outputs any problems it might find with that file
	"""
	lines = open(file_name)
	findings = ''
	print_line = False

	for num,line in enumerate(lines):
		for name,rule in rules['rule_set'][ext]['specific'][os.path.basename(file_name)].iteritems():
			for _regex, truth in rule.iteritems():
				t = re.compile(_regex,re.IGNORECASE)
				if re.search(t,line):
					findings +=  "[SPECIFIC]\t%6d\t%-20s\tFAIL! should be %s\n" % (num+1,name,truth) 
					print_line = True

	if len(findings):
		print file_name
		print findings
	elif print_line == False and rules['print_ok']:
		print file_name + " SPECIFIC CHECK - OK"	
	lines.close()
		

def check_generic_rules(file_name,ext):
	"""
	check_generic_rules -- checks each line of a file for problems
	specified in high/medium/low rules
	will only run the general level if scan_level is set
	"""
	lines = open(file_name)
	findings = ''
	print_line = False
	
	for num,line in enumerate(lines):
		#dump empty lines and lines that begin with a comment
		if re.search('^$',line) or re.search('^\s*#', line) \
			or re.search('^\s*//',line) or re.search('^\s*\|',line) \
			or re.search('^\s*/\*',line) or re.search('^\s*\*',line):
			
			continue
		else:
			for severity,checks in rules['rule_set'][ext]['general'].iteritems():
				if severity not in rules['scan_level']:
					continue
					
				for check in checks:
					if check in rules['ignore']:
						continue
						
					p = re.compile(" "+check,re.IGNORECASE)
					if re.search(p, line):
						findings += "[%s]\t%6d\t%-20s\t%s\n" % (severity.upper(),num+1,check,line[0:100].strip())
						print_line = True

	if len(findings):
		print file_name
		print findings
	elif print_line == False and rules['print_ok']:
		print "GENERIC CHECK - OK\n"
	
	lines.close()

def usage():
	print 'checker.py '
	print "\t[-q | --quick]  - sets scan_level to HIGH and print_ok to FALSE"
	print "\t[-v | --verbose]  - sets scan_level to HIGH,MEDIUM,LOW and print_ok to TRUE"
	print "\t[-t | --topdir <TOPDIRECTORY>] - sets directory to start scan, can be absolute or relative to script"
	print "\t[-f | --folders <FOLDERS>] - comma-separated list of folder names to scan under TOPDIR"
	print "\t[-s | --scan_levels <LEVELS>] - comma-separated list of scan levels (typically HIGH MEDIUM LOW)"
	print "\t[-i | --ignore <IGNORE>] - comma-separated list of patterns to ignore"
	print "\t[-h | --help] - this help screen"
	print
	print 'Basic Examples (quick & verbose):'
	print "\tchecker.py -q -t ~/documents/www/foo"
	print "\tchecker.py -v -t ~/documents/www/foo"
	print
	print 'Example setting custom folders to scan:'
	print "\tchecker.py -f assets -t ~/documents/www/foo"
	print "\tchecker.py --folders application,assets --topdir ~/documents/www/foo"
	print
	print 'Example setting custom scan levels:'
	print "\tchecker.py -s medium -t ~/documents/www/foo"
	print
	print 'Example setting ignore rules with other rules:'
	print '*notice backslash on ` character!*'
	print "\tchecker.py -s high -i print_r,var_dump,\` -t ~/documents/www/foo"
	print
	print "Combination example:"
	print "\tchecker.py -s high -f application -t ~/documents/www/foo"
	
#============================================
# and go
#============================================	
if __name__ == "__main__":
    main(sys.argv[1:])	


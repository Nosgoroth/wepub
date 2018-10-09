#! /usr/bin/python
# -*- coding: utf-8 -*-

import os, sys
try:
	import jstyleson as json
except:
	import json
from optparse import OptionParser

from wepubutils import *
import ebookconvert
import sendtokindle









def main():
	parser = OptionParser(usage="Usage: %prog configFile [options]")
	parser.add_option("-r", "--redownload", action="store_true", dest="nocache", help="Don't use cache")
	parser.add_option("--reprocess", action="store_true", dest="nordbcache", help="Use only raw cache")
	parser.add_option("--polish", action="store_true", dest="polish", help="Polishes the resulting epub")
	parser.add_option("--mobi", action="store_true", dest="mobi", help="Convert to MOBI")
	parser.add_option("--fix-paragraphs", action="store_true", dest="fixparagraphs", help="Fix paragraph styling when converting to MOBI")
	parser.add_option("--kindle", action="store_true", dest="sendtokindle", help="Send to Kindle")
	parser.add_option("--open", action="store_true", dest="open", help="Opens the resulting epub in Calibre's ebook-viewer")
	parser.add_option("-p", "--debug", "--preview", action="store_true", dest="preview", help="Print output of first url and exit")
	parser.add_option("--add", action="store", dest="add", help="Add an URL to the config")

	parser.add_option("--rebuildall", action="store_true", dest="rebuildAll", help="Iterates all configs and rebuilds them all")

	(options, args) = parser.parse_args()

	print

	if options.rebuildAll:
		for file in os.listdir("configs"):
			try:
				print
				fn, ext = os.path.splitext(file)
				CFG = ConfigFile(fn)
				wepubconfig = CFG.read()
				epub = EpubProcessor(wepubconfig)
				epub.make()
			except Exception, ex:
				print
				print "ERROR:", ex
				print
		sys.exit()

	if len(args) < 1:
		print "Please specify a config file name"
		sys.exit()

	options.config = args[0]
	CFG = ConfigFile(options.config)
	wepubconfig = CFG.read()
	if wepubconfig:
		for k in wepubconfig:
			setattr(options, k, wepubconfig[k])
	else:
		sys.exit()

	if options.add:
		if not "urls" in wepubconfig:
			wepubconfig["urls"] = []
		wepubconfig["urls"].append(options.add)
		if CFG.write(wepubconfig):
			print "Added URL to config"
		else:
			print "FAILED to add URL to config"
			sys.exit()


	try: x = options.title_as_header
	except: setattr(options, "title_as_header", True)

	try: x = options.versionid
	except: setattr(options, "versionid", None)

	try: x = options.filters
	except: setattr(options, "filters", [])
	try: x = options.titlefilters
	except: setattr(options, "titlefilters", [])

	if options.nocache:
		print "Cache will be ignored!"
	if options.nordbcache:
		print "Readability cache will be ignored!"


	epub = EpubProcessor(options)
	epub.make()

	print
	print "Wrote epub!"

	if options.open:
		print
		print "Opening epub..."
		ebookconvert.openInEbookViewer(options.outfile)

	if options.polish:
		print
		print "Polishing epub..."
		print
		ebookconvert.polishepub(options.outfile)
		print
		print "Polish complete"

	if options.mobi or options.sendtokindle:

		extraConvertParams = []
		if options.fixparagraphs:
			extraConvertParams += ebookconvert.ConstantFixParagraphOptions

		print
		print "Converting to MOBI..."
		print
		retval = ebookconvert.convertToFormat(options.outfile, 'mobi', extraParams=extraConvertParams)
		print
		print "Conversion completed with exit code", retval

	if options.sendtokindle:
		print
		print "Sending to Kindle, this might take a while...",
		sys.stdout.flush()
		fn, ext = os.path.splitext(options.outfile)
		sendtokindle.sendFromConfig("%s.mobi" % fn)
		print "complete"


if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass
	except:
		raise
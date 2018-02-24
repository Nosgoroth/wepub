#! /usr/bin/python
# -*- coding: utf-8 -*-

import os, sys, importlib
from optparse import OptionParser

from wepubutils import *
from ebookconvert import convertToFormat, polishepub
import sendtokindle









def main():
    parser = OptionParser(usage="Usage: %prog configFile [options]")
    parser.add_option("-r", "--redownload", action="store_true", dest="nocache", help="Don't use cache")
    parser.add_option("--reprocess", action="store_true", dest="nordbcache", help="Use only raw cache")
    parser.add_option("--polish", action="store_true", dest="polish", help="Polishes the resulting epub")
    parser.add_option("--mobi", action="store_true", dest="mobi", help="Convert to MOBI")
    parser.add_option("--kindle", action="store_true", dest="sendtokindle", help="Send to Kindle")
    parser.add_option("-p", "--debug", "--preview", action="store_true", dest="preview", help="Print output of first url and exit")

    (options, args) = parser.parse_args()

    if len(args) < 1:
        print "Please specify a config file name"
        sys.exit()

    options.config = args[0]

    try:
        moduleconfig = importlib.import_module("configs."+options.config)
    except ImportError:
        print "Invalid config:", options.config
        sys.exit()
    except SyntaxError:
        print
        print "Syntax error in config", options.config
        print
        raise

    for k in [item for item in dir(moduleconfig) if not item.startswith("__")]:
        v = moduleconfig.__dict__[k]
        #print k, "=", v
        setattr(options, k, v)

    print

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

    if options.polish:
        print
        print "Polishing epub..."
        print
        polishepub(options.outfile)
        print
        print "Polish complete"

    if options.mobi or options.sendtokindle:
        print
        print "Converting to MOBI..."
        print
        retval = convertToFormat(options.outfile, 'mobi')
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
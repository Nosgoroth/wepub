import os, sys
from optparse import OptionParser

import jncutils, jncapi
import wepubutils
from pushover import pushover



def checkLatestParts(options, verbose=True):
	lastchecked = jncutils.checkinfo.getLastChecked()

	events = jncutils.events.getLatest(filterType=jncutils.EventType.Part, minDate=lastchecked, requestLimit=int(options.limit))
	print "Found", len(events)

	configsToGenerate = []
	latestCheckedEvent = None

	for event in events:
		if not event.process(verbose=verbose):
			continue

		if event.date and (not latestCheckedEvent or latestCheckedEvent < event.date):
			latestCheckedEvent = event.date

		cfgid = event.toConfigFileName()
		if cfgid not in configsToGenerate:
			configsToGenerate.append(cfgid)


	for cfgid in configsToGenerate:
		print
		print
		cfg = wepubutils.ConfigFile(cfgid)
		cfgdata = cfg.read(verbose=False)
		wepubutils.EpubProcessor(cfgdata).make()

	if latestCheckedEvent:
		jncutils.checkinfo.setLastChecked(latestCheckedEvent)





def printLatestEvents(options):
	events = jncutils.events.getLatest(filterType=None, requestLimit=int(options.limit))
	for event in events: print event


def printNextEvents(options):
	events = jncutils.events.getLatest(filterType=None, futureEvents=True, requestLimit=int(options.limit))
	for event in events: print event







def main():
	parser = OptionParser(usage="Usage: %prog [options]")
	parser.add_option("--nocache", action="store_true", dest="nocache", help="Don't use cache when retrieving events from JNC API")
	parser.add_option("--cleardata", action="store_true", dest="cleardata", help="Delete usage memory")
	parser.add_option("--limit", action="store", dest="limit", default=25, help="How many items to get")
	parser.add_option("--check", action="store_true", dest="check", help="Check JNC events and auto add to wepub config")
	parser.add_option("--next", action="store_true", dest="next", help="Print upcoming JNC events")

	(options, args) = parser.parse_args()

	if options.cleardata:
		jncutils.checkinfo.clearData()

	if options.nocache:
		jncutils.events.clearCache()

	if options.check:
		checkLatestParts(options)
	elif options.next:
		printNextEvents(options)
	else:
		printLatestEvents(options)
		


if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass
	except:
		raise
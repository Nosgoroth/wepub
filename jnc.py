import os, sys, re, json
from optparse import OptionParser

import jncutils, jncapi
import wepubutils
from pushover import pushover
from pprint import pprint

import config



def jncTestMethod():
	print "Getting data..."
	data = jncutils.events.getLatest(filterType=None, requestLimit=10)
	pprint(data[0].rawdata)


def checkNotifyManga(options):

	whiteList = []
	blackList = []
	if not options.nofilter:
		whiteList = config.jnc_manga_notify_whitelist
		blackList = config.jnc_manga_notify_blacklist

	networkMangaEvents = jncutils.events.getLatest(filterType=jncutils.EventType.Manga, requestLimit=int(options.limit), whiteList=whiteList, blackList=blackList)
	print "Found", len(networkMangaEvents)

	for event in networkMangaEvents:
		if not jncutils.checkinfo.isNotifiedMangaEvent(event):
			pushover( "[JNC] %s %s" % (event.name, event.details) )
			jncutils.checkinfo.addNotifiedMangaEvent(event)


def processSingleEvent(eventid, verbose=True):
	event = jncutils.events.getEvent(eventid, verbose=False)
	if not event:
		if verbose:
			print "Couldn't retrieve event", eventid
		return
	event.setPreventDefaultQueueing()
	return event.process(verbose=verbose)


def checkLatestParts(options, verbose=True):
	lastprocessed = jncutils.checkinfo.getLastProcessed()

	jncutils.checkinfo.setLastCheckedNow()

	whiteList = []
	blackList = []
	if not options.nofilter:
		whiteList = config.jnc_check_whitelist
		blackList = config.jnc_check_blacklist

	# Get events from API
	networkEvents = jncutils.events.getLatest(filterType=jncutils.EventType.Part, minDate=lastprocessed, requestLimit=int(options.limit), whiteList=whiteList, blackList=blackList)
	print "Found", len(networkEvents)

	# Read errored events to process
	erroredEvents = jncutils.checkinfo.getErroredEvents()
	if erroredEvents and len(erroredEvents) > 0:
		print "Also processing", len(erroredEvents), "errored events"

	# If we have the same event in both lists, take the one from the errored list,
	#   since that one includes error information (like counters)
	erroredEventIds = [e.eventId for e in erroredEvents]
	events = [e for e in networkEvents if e.eventId not in erroredEventIds]
	events += erroredEvents

	configsToGenerate = []
	latestProcessedEvent = None

	for event in events:

		result = event.process(verbose=verbose)

		shouldRegenerateEpub = False
		shouldMarkDateAsProcessed = False
		
		if result == jncutils.EventProcessResultType.Error:

			# Don't regenerate epub, don't save this date as completed
			pass 

		elif result == jncutils.EventProcessResultType.Skipped:

			# Don't regenerate epub, but DO save this date
			shouldMarkDateAsProcessed = True

		elif result == jncutils.EventProcessResultType.Successful:

			# Good! Regenerate and save date.
			shouldRegenerateEpub = True
			shouldMarkDateAsProcessed = True

		else:

			# What the frick!?
			print "Unknown EventProcessResultType", result
			raise Exception("What the frick!?")

		if shouldMarkDateAsProcessed:
			if event.date and (not latestProcessedEvent or latestProcessedEvent < event.date):
				latestProcessedEvent = event.date

		if shouldRegenerateEpub:
			cfgid = event.processedCfgid
			if cfgid not in configsToGenerate:
				configsToGenerate.append(cfgid)

		#Done with the loop iteration


	for cfgid in configsToGenerate:
		print
		print
		cfg = wepubutils.ConfigFile(cfgid)
		cfgdata = cfg.read(verbose=False)
		try:
			wepubutils.EpubProcessor(cfgdata).make()
		except Exception, ex:
			print ex
			#raise
			pushover("[JNC] Error generating %s: %s" % (cfgid, ex) )

	if latestProcessedEvent:
		jncutils.checkinfo.setLastProcessed(latestProcessedEvent)




def generateVolumeConfigsFromSeriesUrl(url):
	r = re.search(r'https?\:\/\/[^\/]+\/s\/([^\/?]+)', url)
	if not r:
		print "Invalid URL"
		return
	slug = r.group(1)
	print "Using slug:", slug

	print "Retrieving series..."
	series = jncapi.getSeriesFromSlug(slug)
	if not series:
		print "ERROR: Unable to retrieve series"
		return

	for volume in series["volumes"]:
		print 
		print volume["title"]

		generateVolumeConfig(volume)


def generateVolumeConfigFromUrl(url):
	r = re.search(r'https?\:\/\/[^\/]+\/v\/([^\/?]+)', url)
	if not r:
		raise Exception("Invalid URL")
	slug = r.group(1)
	print "Using slug:", slug

	print "Retrieving volume..."
	volume = jncapi.getVolumeFromSlug(slug)
	if not volume:
		raise Exception("ERROR: Unable to retrieve volume")

	return generateVolumeConfig(volume)

def generateVolumeConfig(volume):
	cfgid = jncutils.volumeNameToConfigFileName(volume["title"])
	print "Using config name:", cfgid

	cfg = wepubutils.ConfigFile(cfgid)
	cfgdata = cfg.read(verbose=False)

	if cfgdata:
		print "Config already exists!"
		return False

	cfgdata = jncutils.generateVolumeConfigDict(volume)

	cfgdata["urls"] = jncutils.getVolumeUrls(volume)

	saved = cfg.write(cfgdata, createNew=True, verbose=False)
	cfgdata = cfg.read(verbose=False)
	if not saved or not cfgdata:
		raise Exception("ERROR creating new config!")

	wepubutils.EpubProcessor(cfgdata).make()
	return True





def printLatestEvents(options):

	whiteList = []
	blackList = []
	if not options.nofilter:
		whiteList = config.jnc_list_whitelist
		blackList = config.jnc_list_blacklist

	events = jncutils.events.getLatest(filterType=None, requestLimit=int(options.limit), whiteList=whiteList, blackList=blackList)
	for event in events: print event


def printNextEvents(options):

	whiteList = []
	blackList = []
	if not options.nofilter:
		whiteList = config.jnc_list_whitelist
		blackList = config.jnc_list_blacklist

	events = jncutils.events.getLatest(filterType=None, futureEvents=True, requestLimit=int(options.limit), whiteList=whiteList, blackList=blackList)
	for event in events: print event


def printIcalNextEvents(options):

	whiteList = []
	blackList = []
	if not options.nofilter:
		whiteList = config.jnc_calendar_whitelist
		blackList = config.jnc_calendar_blacklist
		
	events = jncutils.events.getLatest(verbose=False, filterType=None, futureEvents=True, requestLimit=int(options.limit), whiteList=whiteList, blackList=blackList)
	jncutils.printIcal(config.jnc_calendar_name, events)



def printEventJson(options):

	whiteList = []
	blackList = []
	if not options.nofilter:
		whiteList = config.jnc_list_whitelist
		blackList = config.jnc_list_blacklist

	events = []

	if options.jsonnext:
		limit = options.jsonnextlimit if options.jsonnextlimit else options.limit
		events += jncutils.events.getLatest(verbose=False, filterType=None, futureEvents=True, requestLimit=int(limit), whiteList=whiteList, blackList=blackList)
		events.reverse()

	events += jncutils.events.getLatest(verbose=False, filterType=None, futureEvents=False, requestLimit=int(options.limit), whiteList=whiteList, blackList=blackList)


	print '[[[JSON]]]'+json.dumps([x.asSimpleDict() for x in events])+'[[[/JSON]]]'


def main():
	parser = OptionParser(usage="Usage: %prog [options]")
	parser.add_option("--nocache", action="store_true", dest="nocache", help="Don't use cache when retrieving events from JNC API")
	parser.add_option("--cleardata", action="store_true", dest="cleardata", help="Delete usage memory")
	parser.add_option("--limit", action="store", dest="limit", default=25, help="How many items to get")
	parser.add_option("--check", action="store_true", dest="check", help="Check JNC events and auto add to wepub config")
	parser.add_option("--checkmanga", action="store_true", dest="checkmanga", help="Check JNC manga events and notify")
	parser.add_option("--next", action="store_true", dest="next", help="Print upcoming JNC events")
	parser.add_option("--ical", action="store_true", dest="ical", help="Print upcoming JNC events in Ical format")
	parser.add_option("--nofilter", action="store_true", dest="nofilter", help="Ignore configured whitelists and blacklists")
	parser.add_option("--genvolume", action="store", dest="genvolume", help="Generate config from volume URL")
	parser.add_option("--genseries", action="store", dest="genseries", help="Generate configs from series URL")
	parser.add_option("--event", action="store", dest="eventid", help="Process a single event")

	parser.add_option("--test", action="store_true", dest="test", help="Calls a test method")
	parser.add_option("--json", action="store_true", dest="json", help="Print events as json")
	parser.add_option("--json-include-next", action="store_true", dest="jsonnext", help="Include future events in json")
	parser.add_option("--json-next-limit", action="store", dest="jsonnextlimit", help="How many future events to include in json")

	(options, args) = parser.parse_args()

	if options.test:
		jncTestMethod()
		return

	if options.cleardata:
		jncutils.checkinfo.clearData()

	if options.nocache:
		jncutils.events.clearCache()

	if options.eventid:
		processSingleEvent(options.eventid)
	elif options.check:
		checkLatestParts(options)
		checkNotifyManga(options)
	elif options.checkmanga:
		checkNotifyManga(options)
	elif options.genvolume:
		generateVolumeConfigFromUrl(options.genvolume)
	elif options.genseries:
		generateVolumeConfigsFromSeriesUrl(options.genseries)
	elif options.next:
		printNextEvents(options)
	elif options.ical:
		printIcalNextEvents(options)
	elif options.json:
		printEventJson(options)
	else:
		printLatestEvents(options)
		


if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass
	except:
		raise

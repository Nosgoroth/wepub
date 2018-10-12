import os, sys
from optparse import OptionParser

import jncutils, jncapi
import wepubutils
from pushover import pushover



def checkLatestParts(options, verbose=True):
	lastchecked = jncutils.checkinfo.getLastChecked()

	# Get events from API
	networkEvents = jncutils.events.getLatest(filterType=jncutils.EventType.Part, minDate=lastchecked, requestLimit=int(options.limit))
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
	latestCheckedEvent = None

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
			if event.date and (not latestCheckedEvent or latestCheckedEvent < event.date):
				latestCheckedEvent = event.date

		if shouldRegenerateEpub:
			cfgid = event.toConfigFileName()
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
			pushover("Error generating %s: %s" % (cfgid, ex) )


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
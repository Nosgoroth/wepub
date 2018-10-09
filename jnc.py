import os, sys
from optparse import OptionParser

import jncutils, jncapi
import wepubutils
from pushover import pushover


def main():
	parser = OptionParser(usage="Usage: %prog [options]")
	parser.add_option("--nocache", action="store_true", dest="nocache", help="Don't use cache when retrieving events from JNC API")
	parser.add_option("--cleardata", action="store_true", dest="cleardata", help="Delete usage memory")
	parser.add_option("--limit", action="store", dest="limit", default=25, help="How many items to get")
	parser.add_option("--check", action="store_true", dest="check", help="Check JNC events and auto add to wepub config")

	(options, args) = parser.parse_args()

	if options.cleardata:
		jncutils.checkinfo.clearData()

	if options.nocache:
		jncutils.events.clearCache()

	if options.check:
		lastchecked = jncutils.checkinfo.getLastChecked()
		events = jncutils.events.getLatest(filterType=jncutils.EventType.Part, minDate=lastchecked, requestLimit=int(options.limit))
		print "Found", len(events)
		for event in events:

			try:

				print
				print "Found %s %s" % (event.name, event.details)

				cfgid = "jnc_"+event.toConfigFileName()
				cfg = wepubutils.ConfigFile(cfgid)
				cfgdata = cfg.read(verbose=False)

				if not cfgdata:
					cfgdata = {}
					cfgdata["title"] = event.name
					cfgdata["outfile"] = "out/jnc/"+event.toEpubFileName()+".epub"
					cfgdata["urls"] = []

					volume = event.getVolume()
					if volume:
						cfgdata["author"] = volume["author"]
						cfgdata["cover"] = jncapi.getCoverFullUrlForAttachmentContainer(volume)
					else:
						print "Couldn't get volume data"

					saved = cfg.write(cfgdata, createNew=True, verbose=False)
					cfgdata = cfg.read(verbose=False)
					if not saved or not cfgdata:
						print "ERROR creating new config!"
						event.pushoverError("ERROR creating new config")
						continue

				url = event.getUrl()

				if not "urls" in cfgdata:
					cfgdata["urls"] = []
				if url in cfgdata["urls"]:
					print "Part already exists! Ignoring..."
					continue
				cfgdata["urls"].append(url)
				cfgdata["urls"] = jncutils.sortContentUrlsByPartNumber(cfgdata["urls"])
				if cfg.write(cfgdata, verbose=False):
					pass
				else:
					print "FAILED to add URL to config"
					event.pushoverError("FAILED to add URL to config")
					continue

				title, html = event.getPartContent()
				if not html:
					print "FAILED to retrieve part content"
					event.pushoverError("FAILED to retrieve part content")
					continue
				else:
					pass
					#print "Got content:"
					#print "   ", title
					#print "   ", html[:30]

				print "Saving content to cache...",
				html = '<html><head></head><body>%s</body>' % html
				wepubutils.retrieveUrl(url, setCacheContent=html, setCacheReadable=html, setCacheTitle=title)
				print "done."

				print "Making epub...",
				processor = wepubutils.EpubProcessor(cfgdata)
				processor.make()
				print "done."

				event.pushoverOk()
			except Exception, e:
				print
				print "ERROR PROCESSING EVENT"
				print
				print e
				print
				print
				#raise
				

		jncutils.checkinfo.setLastCheckedNow()
	else:
		events = jncutils.events.getLatest(filterType=jncutils.EventType.Part, requestLimit=25)
		for event in events:
			print event
			title, html = event.getPartContent()
			if html:
				print(title)
				print(html[:100])


if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass
	except:
		raise
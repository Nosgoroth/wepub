#! /usr/bin/python
# -*- coding: utf-8 -*-

import os, sys, re
from optparse import OptionParser
import feedparser
from wepubutils import *
import config as wepubconfig
from pprint import pprint
from datetime import datetime
from time import mktime
from pushover import pushover


class WepubRssCheckInfo():
	datafn = None
	data = None

	def __init__(self):
		self.datafn = os.path.join(os.path.dirname(__file__),".wepubrssinfo.json")
		try: self.load()
		except: pass

	def clearData(self):
		if not os.path.exists(self.datafn): return
		os.remove(self.datafn)
		self.load()

	def load(self):
		if os.path.exists(self.datafn):
			with open(self.datafn) as f:
				self.data = json.load(f)
		else:
			self.data = {}
	def save(self):
		with open(self.datafn, 'w') as f:
			json.dump(self.data, f)

	def getLastSeen(self, rssurl):
		t = self.data[rssurl] if rssurl in self.data else "1970-01-01 00:00:00"
		return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")

	def setLastSeen(self, rssurl, dt, nosave=False):
		self.data[rssurl] = dt.strftime("%Y-%m-%d %H:%M:%S")
		if not nosave: self.save()

	def setLastSeenNow(self, rssurl, nosave=False):
		self.setLastSeen(rssurl, datetime.now(), nosave=nosave)


wrcheckinfo = WepubRssCheckInfo()



def parseRss(rssdef):
	url = rssdef["url"]
	rssid = rssdef["id"] if "id" in rssdef else url

	print
	print "Processing feed", rssid

	d = feedparser.parse(url)
	lastseen = wrcheckinfo.getLastSeen(rssid)
	newlastseen = lastseen

	configs = {}
	configstoprocess = []

	found = 0
	added = 0

	for post in reversed(d.entries):
		dt = datetime.fromtimestamp(mktime(post.published_parsed))
		if dt <= lastseen:
			continue

		found += 1

		if dt > newlastseen:
			newlastseen = dt

		print
		print "Found post:", post.title

		targetconfig = rssdef["config"] if "config" in rssdef else None
		if "configs" in rssdef:
			for pattern, pconfig in rssdef["configs"]:
				if re.search(pattern, post.title):
					targetconfig = pconfig

		if not targetconfig:
			print "Couldn't find a target config - no match"
			pushover( "[WepubRSS] No matching config for %s" % (post.title) )
			continue

		if targetconfig in configs:
			CFG = configs[targetconfig]
		else:
			CFG = ConfigFile(targetconfig)
			configs[targetconfig] = CFG

		if not CFG.addUrl(post.link):
			print "Couldn't add URL"
			pushover( "[WepubRSS] Couldn't auto-add URL for %s" % (post.title) )
			continue
		else:
			print "Added to config:", targetconfig

		added += 1		

		if not targetconfig in configstoprocess:
			configstoprocess.append(targetconfig)

		pushover( "[WepubRSS] %s" % (post.title) )

	if newlastseen > lastseen:
		wrcheckinfo.setLastSeen(rssid, newlastseen)

	print
	print "Found", found, "; Added", added, "; Configs to process", len(configstoprocess)

	for configname in configstoprocess:
		epub = EpubProcessor(configs[configname].read())
		epub.make()



def main():
	parser = OptionParser(usage="Usage: %prog [options]")
	parser.add_option("--cleardata", action="store_true", dest="cleardata", help="Delete usage memory")

	(options, args) = parser.parse_args()

	if options.cleardata:
		wrcheckinfo.clearData()

	if wepubconfig.wepub_rss_enabled and len(wepubconfig.wepub_rss_feeds) > 0:

		for rssdef in wepubconfig.wepub_rss_feeds:
			parseRss(rssdef)

	else:

		print "Disabled in config"





if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass
	except:
		raise
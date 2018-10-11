#!/usr/local/bin/python3

import os, sys, json, time, re
from pprint import pprint
from datetime import datetime

import jncapi, wepubutils
from pushover import pushover

JNCSite = "https://j-novel.club"
JNCAPIEndpoint = "https://api.j-novel.club/api"


class EventCheckInfo():

	MAX_RETRY_HOURS = 24
	HOURS_BETWEEN_ATTEMPTS = 2

	datafn = None
	data = None

	def __init__(self):
		self.datafn = os.path.join(os.path.dirname(__file__),".jnceventcheckinfo.json")
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

	def getLastChecked(self):
		t = self.data["lastChecked"] if "lastChecked" in self.data else "1970-01-01 00:00"
		return datetime.strptime(t, "%Y-%m-%d %H:%M")

	def setLastChecked(self, dt):
		self.data["lastChecked"] = dt.strftime("%Y-%m-%d %H:%M")
		self.save()

	def setLastCheckedNow(self):
		self.setLastChecked(datetime.now())

	def addErroredEvent(self, event):
		if "erroredEvents" not in self.data or not isinstance(self.data["erroredEvents"], dict):
			self.data["erroredEvents"] = {}

		self.data["erroredEvents"][event.eventId] = event.getRawdata()
		self.save()

	def removeErroredEvent(self, eventId):
		if isinstance(eventId, Event):
			eventId = eventId.eventId
		if "erroredEvents" not in self.data or not isinstance(self.data["erroredEvents"], dict):
			return False
		if not eventId in self.data["erroredEvents"]:
			return False
		self.data["erroredEvents"].pop(event.eventId, None)
		self.save()
		return True

	def clearErroredEvents(self):
		self.data["erroredEvents"] = None
		self.save()

	def getErroredEvents(self):
		if "erroredEvents" not in self.data or not isinstance(self.data["erroredEvents"], dict):
			return []

		now = datetime.now()

		maxretries = self.MAX_RETRY_HOURS / self.HOURS_BETWEEN_ATTEMPTS

		events = []

		for eventId, rawevent in self.data["erroredEvents"].iteritems():
			event = Event(rawevent)

			if event.lastErrorDate:
				td = now - event.lastErrorDate
				th = td.total_seconds() / (60*60)
				if th < self.HOURS_BETWEEN_ATTEMPTS:
					continue

			if event.errorCounter >= maxretries:
				#self.removeErroredEvent(event)
				continue

			event.setErrored()
			events.append(event)

		return events





class EventGetter():
	cachefn = None

	def __init__(self):
		self.cachefn = os.path.join(os.path.dirname(__file__),".jncevents.cache.json")
		
	def clearCache(self):
		if not os.path.exists(self.cachefn): return
		os.remove(self.cachefn)

	def getLatest(self, filterType=None, minDate=None, maxDate=None, requestLimit=50, cacheMinutes=60, reverse=False, futureEvents=False):
		if os.path.exists(self.cachefn) and os.path.getmtime(self.cachefn) > time.time()-60*cacheMinutes:

			print("Using cached events.")
			print

			with open(self.cachefn) as f:
				events = json.load(f)

		else:

			filterlimit = requestLimit if requestLimit is not None else 200
			url = "/events?filter[limit]="+str(filterlimit)
			if futureEvents:
				url += "&filter[order]=date%20ASC&filter[where][date][gt]="+datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
			else:
				url += "&filter[order]=date%20DESC&filter[where][date][lt]="+datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
			
			#print url
			print "Getting latest events...",
			events = jncapi.request(url)
			print("done.")
			print

			with open(self.cachefn, 'w') as f:
				json.dump(events, f)

		if reverse: events.reverse()

		eventobjs = []
		for rawevent in events:
			evt = Event(rawevent)
			if filterType is not None and evt.eventType != filterType:
				continue
			if minDate is not None and minDate >= evt.date:
				continue
			if maxDate is not None and maxDate <= evt.date:
				continue
			eventobjs.append(evt)

		return eventobjs

events = EventGetter()
checkinfo = EventCheckInfo()

class EventType():
	Unknown = 0
	Part = 1
	Volume = 2
	Other = 3


class Event():
	rawdata = None
	eventType = EventType.Unknown
	eventId = None
	name = None
	partNum = None
	volumeNum = None
	finalPart = False
	date = None
	details = None
	linkFragment = None

	errorCounter = 0
	errored = False
	lastErrorDate = None

	def __init__(self, rawdata):
		self.rawdata = rawdata
		date = rawdata["date"]
		self.name = rawdata["name"]
		self.details = rawdata["details"]
		self.eventId = rawdata["id"]
		self.linkFragment = rawdata["linkFragment"]

		if "errorCounter" in self.rawdata:
			self.errorCounter = self.rawdata["errorCounter"]

		if "lastErrorDate" in self.rawdata:
			self.lastErrorDate = datetime.strptime(self.rawdata["lastErrorDate"], "%Y-%m-%dT%H:%M:%S")

		r = re.search(r'^([\d\-]+T[\d\:]+)\.', date)
		self.date = datetime.strptime(r.group(1), "%Y-%m-%dT%H:%M:%S")

		rpart = re.search(r'Part ([\d]+)([\s] FINAL)?', self.details)
		if rpart:
			self.eventType = EventType.Part
			self.partNum = int(rpart.group(1))
			self.finalPart = (rpart.group(2) is not None)
		elif self.details == "Ebook Publishing":
			self.eventType = EventType.Volume
		else:
			self.eventType = EventType.Other

		#For when the event name just doesn't include the volume number
		r = re.search(r'(Volume|Vol|Vol\.)\s?([\d]+)?\s?', self.details)
		if r:
			self.volumeNum = int(r.group(2))

		r = re.search(r'(Volume|Vol|Vol\.) ([\d]+)?\s?', self.name)
		if not r and self.volumeNum:
			self.name += " Vol. "+str(self.volumeNum)
		elif not self.volumeNum and r:
			self.volumeNum = int(r.group(2))

	def getRawdata(self):
		if self.errorCounter > 0:
			self.rawdata["errorCounter"] = self.errorCounter
		if self.lastErrorDate:
			self.rawdata["lastErrorDate"] = self.lastErrorDate.strftime("%Y-%m-%dT%H:%M:%S")
		return self.rawdata

	def setErrored(self):
		self.errored = True

	def incrementErrorCounter(self):
		self.lastErrorDate = datetime.now()
		self.errorCounter += 1

	def process(self, verbose=True):
		try:
			if verbose:
				print
				print "Found %s %s" % (self.name, self.details)

			cfgid = self.toConfigFileName()
			cfg = wepubutils.ConfigFile(cfgid)
			cfgdata = cfg.read(verbose=False)

			if not cfgdata:
				cfgdata = {}
				cfgdata["title"] = self.name
				cfgdata["outfile"] = "out/jnc/"+self.toEpubFileName()+".epub"
				cfgdata["urls"] = []

				volume = self.getVolume()
				if volume:
					cfgdata["author"] = volume["author"]
					cfgdata["cover"] = jncapi.getCoverFullUrlForAttachmentContainer(volume)
				else:
					print "Couldn't get volume data"

				saved = cfg.write(cfgdata, createNew=True, verbose=False)
				cfgdata = cfg.read(verbose=False)
				if not saved or not cfgdata:
					self.setError("ERROR creating new config")
					return False

			url = self.getUrl()

			if not "urls" in cfgdata:
				cfgdata["urls"] = []
			if url in cfgdata["urls"]:
				print "Part already exists! Ignoring..."
				return True
			cfgdata["urls"].append(url)
			cfgdata["urls"] = sortContentUrlsByPartNumber(cfgdata["urls"])
			if cfg.write(cfgdata, verbose=False):
				pass
			else:
				self.setError("FAILED to add URL to config")
				return False

			title, html = self.getPartContent()
			if not html:
				self.setError("FAILED to retrieve part content")
				return False

			print "Saving content to cache...",
			html = '<html><head></head><body>%s</body>' % html
			wepubutils.retrieveUrl(url, setCacheContent=html, setCacheReadable=html, setCacheTitle=title)
			print "done."

			self.pushoverOk()

			return True
		except Exception, e:
			print
			print "ERROR PROCESSING EVENT"
			print
			print e
			print
			print
			return False
			self.setError("EXCEPTION: "+e)

	def setError(self, errorMsg):
		print "ERROR:", errorMsg
		self.incrementErrorCounter()
		self.pushoverError(errorMsg)

	def pushoverOk(self):
		pushover( "[JNC] %s %s" % (self.name, self.details) )

	def pushoverError(self, error="Unknown"):
		pushover( "[JNC][ERROR] %s %s (%s)" % (self.name, self.details, error) )

	def __str__(self):
		return ("[%s] %s - %s" % (self.date.strftime("%Y-%m-%d %H:%M"), self.name, self.details))

	def isPart(self):
		return (self.eventType == EventType.Part)

	def isFinalPart(self):
		return ((self.eventType == EventType.Part) and self.finalPart)

	def isVolume(self):
		return (self.eventType == EventType.Volume)

	def getUrl(self):
		return JNCSite+self.linkFragment

	def toConfigFileName(self):
		n = re.sub(r'[^\d\w]', "_", self.name)
		n = re.sub(r'_+', '_', n)
		return "jnc_"+n

	def toEpubFileName(self):
		n = re.sub(r'[^\d\w\.\s\_\-\,\!]', "_", self.name)
		n = re.sub(r'_+', '_', n)
		return n

	def getSeries(self):
		if not self.isPart():
			return None

		slug = re.sub(r"^\/c\/", "", self.linkFragment)
		part = jncapi.getPartFromSlug(slug)
		if not part or not "serieId" in part:
			print "Error retrieving event part"
			return None
		series = jncapi.getSeries(part["serieId"])
		
		return series

	def getVolume(self):
		if not self.isPart():
			return None

		slug = re.sub(r"^\/c\/", "", self.linkFragment)
		part = jncapi.getPartFromSlug(slug)
		if not part or not "volumeId" in part:
			print "Error retrieving event part"
			return None
		series = jncapi.getVolume(part["volumeId"])

		return series

	def getPartContent(self):
		if not self.isPart():
			return (None, None)
		slug = re.sub(r"^\/c\/", "", self.linkFragment)
		part = jncapi.getPartFromSlug(slug)
		if not part or not "id" in part:
			print "Error retrieving event part"
			return (None, None)
		partid = part["id"]
		partdata = jncapi.getPartData(partid)
		if not partdata or "dataHTML" not in partdata:
			print "Error retrieving event part data"
			return (None, None)
		return (part["title"], partdata["dataHTML"])



def sortContentUrlsByPartNumber(urls):
	x = []
	for url in urls:
		n = 999
		rpart = re.search(r'part-([\d]+)(-final)?$', url)
		if rpart:
			n = int(rpart.group(1))
		x.append((n, url))
	x = sorted(x, key=lambda x: x[0])
	return [t[1] for t in x]
			


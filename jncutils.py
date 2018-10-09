#!/usr/local/bin/python3

import os, sys, json, time, re
from pprint import pprint
from datetime import datetime

import jncapi
from pushover import pushover

JNCSite = "https://j-novel.club"
JNCAPIEndpoint = "https://api.j-novel.club/api"


class EventCheckInfo():
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



class EventGetter():
	cachefn = None

	def __init__(self):
		self.cachefn = os.path.join(os.path.dirname(__file__),".jncevents.cache.json")
		
	def clearCache(self):
		if not os.path.exists(self.cachefn): return
		os.remove(self.cachefn)

	def getLatest(self, filterType=None, minDate=None, requestLimit=50, cacheMinutes=60, reverse=False, futureEvents=False):
		if os.path.exists(self.cachefn) and os.path.getmtime(self.cachefn) > time.time()-60*cacheMinutes:

			print("Using cached events.")
			print

			with open(self.cachefn) as f:
				events = json.load(f)

		else:

			filterlimit = requestLimit if requestLimit is not None else 200
			url = "/events?filter[limit]="+str(filterlimit)
			if not futureEvents:
				url += "&filter[where][date][lt]="+datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
			
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
			print rawevent
			evt = Event(rawevent)
			if filterType is not None and evt.eventType != filterType:
				continue
			if minDate is not None and minDate > evt.date:
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
	eventType = EventType.Unknown
	eventId = None
	name = None
	partNum = None
	finalPart = False
	date = None
	details = None
	linkFragment = None

	def __init__(self, rawdata):
		date = rawdata["date"]
		self.name = rawdata["name"]
		self.details = rawdata["details"]
		self.eventId = rawdata["id"]
		self.linkFragment = rawdata["linkFragment"]

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
			


#!/usr/local/bin/python3

import os, sys, json, time, re, calendar
from pprint import pprint
from datetime import datetime, timedelta

import jncapi, wepubutils
from pushover import pushover
import config



def utc_to_local(utc_dt):
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)


class EventCheckInfo():

	MAX_RETRY_HOURS = 24
	HOURS_BETWEEN_ATTEMPTS = 2
	MAX_KEEP_SUCCESSFUL_EVENTS = 20
	MAX_KEEP_NOTIFIED_MANGA_EVENTS = 50
	MAX_KEEP_ERROR_DAYS = 30

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

	def setLastChecked(self, dt, nosave=False):
		self.data["lastChecked"] = dt.strftime("%Y-%m-%d %H:%M")
		if not nosave: self.save()

	def setLastCheckedNow(self, nosave=False):
		self.setLastChecked(datetime.now(), nosave=nosave)


	def getLastProcessed(self):
		t = self.data["lastProcessed"] if "lastProcessed" in self.data else "1970-01-01 00:00"
		return datetime.strptime(t, "%Y-%m-%d %H:%M")

	def setLastProcessed(self, dt, nosave=False):
		self.data["lastProcessed"] = dt.strftime("%Y-%m-%d %H:%M")
		if not nosave: self.save()

	def setLastProcessedNow(self, nosave=False):
		self.setLastProcessed(datetime.now(), nosave=nosave)


	def addSuccessfulEvent(self, event, nosave=False):
		self.removeErroredEvent(event, nosave=True)

		if "successfulEvents" not in self.data or not isinstance(self.data["successfulEvents"], dict):
			self.data["successfulEvents"] = {}

		self.data["successfulEvents"][event.eventId] = event.getRawdata()
		self.trimSuccessfulEvents(nosave=nosave)


	def trimSuccessfulEvents(self, nosave=False):
		if "successfulEvents" not in self.data or not isinstance(self.data["successfulEvents"], dict):
			self.data["successfulEvents"] = {}
		x = []
		for eventId in self.data["successfulEvents"]:
			event = Event(self.data["successfulEvents"][eventId])

			x.append((event, event.date))
		x = sorted(x, key=lambda x: x[1], reverse=True)
		x = [t[0] for t in x]

		self.data["successfulEvents"] = {}
		for event in x[:self.MAX_KEEP_SUCCESSFUL_EVENTS]:
			self.data["successfulEvents"][event.eventId] = event.getRawdata()

		if not nosave: self.save()

	def addNotifiedMangaEvent(self, event, nosave=False):
		if "notifiedMangaEvents" not in self.data or not isinstance(self.data["notifiedMangaEvents"], dict):
			self.data["notifiedMangaEvents"] = {}

		self.data["notifiedMangaEvents"][event.eventId] = event.getRawdata()
		self.trimNotifiedMangaEvents(nosave=nosave)

	def isNotifiedMangaEvent(self, event):
		if "notifiedMangaEvents" not in self.data or not isinstance(self.data["notifiedMangaEvents"], dict):
			self.data["notifiedMangaEvents"] = {}

		return event.eventId in self.data["notifiedMangaEvents"]


	def trimNotifiedMangaEvents(self, nosave=False):
		if "notifiedMangaEvents" not in self.data or not isinstance(self.data["notifiedMangaEvents"], dict):
			self.data["notifiedMangaEvents"] = {}
		x = []
		for eventId in self.data["notifiedMangaEvents"]:
			event = Event(self.data["notifiedMangaEvents"][eventId])

			x.append((event, event.date))
		x = sorted(x, key=lambda x: x[1], reverse=True)
		x = [t[0] for t in x]

		self.data["notifiedMangaEvents"] = {}
		for event in x[:self.MAX_KEEP_NOTIFIED_MANGA_EVENTS]:
			self.data["notifiedMangaEvents"][event.eventId] = event.getRawdata()

		if not nosave: self.save()
		

	def addErroredEvent(self, event, nosave=False):
		if "erroredEvents" not in self.data or not isinstance(self.data["erroredEvents"], dict):
			self.data["erroredEvents"] = {}

		self.data["erroredEvents"][event.eventId] = event.getRawdata()

		self.trimErroredEvents(nosave=True)
		if not nosave: self.save()

	def removeErroredEvent(self, eventId, nosave=False):
		if isinstance(eventId, Event):
			eventId = eventId.eventId
		if "erroredEvents" not in self.data or not isinstance(self.data["erroredEvents"], dict):
			return False
		if not eventId in self.data["erroredEvents"]:
			return False
		self.data["erroredEvents"].pop(eventId, None)
		if not nosave: self.save()
		return True

	def clearErroredEvents(self, nosave=False):
		self.data["erroredEvents"] = None
		if not nosave: self.save()

	def getErroredEvents(self, ignoreEvents=[]):
		if "erroredEvents" not in self.data or not isinstance(self.data["erroredEvents"], dict):
			return []

		now = datetime.now()

		maxretries = self.MAX_RETRY_HOURS / self.HOURS_BETWEEN_ATTEMPTS

		events = []
		eventIdsToIgnore = [e.eventId for e in ignoreEvents]

		self.trimErroredEvents()

		for eventId, rawevent in self.data["erroredEvents"].iteritems():
			event = Event(rawevent)

			if event.eventId in eventIdsToIgnore:
				continue

			if event.lastErrorDate:
				td = now - event.lastErrorDate
				th = td.total_seconds() / (60*60)
				if th < self.HOURS_BETWEEN_ATTEMPTS:
					# Don't attempt now
					event.setPreventProcessing()

			if event.errorCounter >= maxretries:
				event.setPreventProcessing()

			event.setAsErrored()
			events.append(event)

		return events


	def trimErroredEvents(self, nosave=False):
		if "erroredEvents" not in self.data or not isinstance(self.data["erroredEvents"], dict):
			self.data["erroredEvents"] = {}

		# MAX_KEEP_ERROR_DAYS
		now = datetime.now()

		eventsToRemove = []

		for eventId in self.data["erroredEvents"]:
			event = Event(self.data["erroredEvents"][eventId])
			td = now - event.date
			tdays = td.total_seconds() / (60*60*24)
			if tdays > self.MAX_KEEP_ERROR_DAYS:
				eventsToRemove.append(eventId)

		for eventId in eventsToRemove:
			self.removeErroredEvent(eventId, nosave=True)

		if not nosave: self.save()









class EventGetter():
	cachefn = None

	def __init__(self):
		self.cachefn = os.path.join(os.path.dirname(__file__),".jncevents.cache.json")
		
	def clearCache(self):
		if not os.path.exists(self.cachefn): return
		os.remove(self.cachefn)

	def getEvent(self, eventid, verbose=True):
		rawevent = jncapi.getEvent(eventid, verbose=verbose)
		if rawevent:
			return Event(rawevent)
		else:
			return None

	def getLatest(self, verbose=True, filterType=None, minDate=None, maxDate=None, requestLimit=50, cacheMinutes=60, reverse=False, futureEvents=False, whiteList=None, blackList=None):
		
		utcnow = datetime.utcnow()

		if config.jnc_use_cache and os.path.exists(self.cachefn) and os.path.getmtime(self.cachefn) > time.time()-60*cacheMinutes:

			if verbose:
				print "Using cached events."
				print

			with open(self.cachefn) as f:
				events = json.load(f)

		else:

			filterlimit = requestLimit if requestLimit is not None else 200

			url = "/events?filter[limit]="+str(filterlimit)
			if futureEvents:
				utcnow_str = (utcnow - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%S")
				url += "&filter[order]=date%20ASC&filter[where][date][gt]="+utcnow_str
			else:
				utcnow_str = (utcnow + timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%S")
				url += "&filter[order]=date%20DESC&filter[where][date][lt]="+utcnow_str
			
			#print url
			if verbose: print "Getting latest events...",
			events = jncapi.request(url, verbose=verbose)
			if verbose:
				print "done."
				print

			with open(self.cachefn, 'w') as f:
				json.dump(events, f)

		if reverse: events.reverse()

		eventobjs = []
		for rawevent in events:
			evt = Event(rawevent)

			# print evt.date

			if futureEvents and evt.date < utcnow:
				continue
			elif not futureEvents and evt.date > utcnow:
				continue

			if not evt.inWhitelist(whiteList):
				continue

			if evt.inBlacklist(blackList):
				continue

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
	Manga = 4

	@staticmethod
	def FromString(strConvert):
		try:
			return getattr(EventType, strConvert)
		except:
			return None


class EventProcessResultType():
	Error = 0
	Successful = 1
	Skipped = 2
	AlreadyProcessed = 3







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

	processedCfgid = None

	errorCounter = 0
	errored = False
	lastErrorDate = None

	preventProcessing = False

	preventDefaultQueueing = False

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

		if self.details == "Ebook Publishing":
			self.eventType = EventType.Volume
		else:
			rpart = re.search(r'Part ([\d]+)([\s]+FINAL)?', self.details)
			if rpart:
				self.eventType = EventType.Part
				self.partNum = int(rpart.group(1))
				self.finalPart = (rpart.group(2) is not None)
			else:
				rpart = re.search(r'Parts ([\d]+).*([\s]+FINAL)?', self.details)
				if rpart:
					self.eventType = EventType.Part
					self.partNum = int(rpart.group(1))
					self.finalPart = (rpart.group(2) is not None)
				else:
					rpart = re.search(r'Chapter ([\d]+)([\s]+FINAL)?', self.details)
					if rpart:
						self.eventType = EventType.Manga
						self.partNum = int(rpart.group(1))
						self.finalPart = (rpart.group(2) is not None)
					else:
						self.eventType = EventType.Other

		#For when the event name just doesn't include the volume number
		r = re.search(r'(Volume|Vol|Vol\.)\s?([\d]+)?\s?', self.details)
		if r:
			try:
				self.volumeNum = int(r.group(2))
			except:
				self.volumeNum = 1

		r = re.search(r'(Volume|Vol|Vol\.) ([\d]+)?\s?', self.name)
		if not r and self.volumeNum:
			self.name += " Vol. "+str(self.volumeNum)
		elif not self.volumeNum and r:
			try:
				self.volumeNum = int(r.group(2))
			except:
				self.volumeNum = 1


	def asSimpleDict(self):
		return {
			"eventType": self.eventType,
			"eventId": self.eventId,
			"name": self.name,
			"partNum": self.partNum,
			"volumeNum": self.volumeNum,
			"finalPart": self.finalPart,
			"timestamp": calendar.timegm(self.date.timetuple()),
			"details": self.details,
			"linkFragment": self.linkFragment,
			"url": self.getUrl()
		}

	def inMatchlist(self, matchList, matchProp, onNoMatchList=True):
		if not matchList: return onNoMatchList
		for listMatcher in matchList:
			matcherStr = listMatcher
			
			if isinstance(listMatcher, list) or isinstance(listMatcher, tuple):
				matcherStr, desiredTypeStr = listMatcher
				desiredType = EventType.FromString(desiredTypeStr)
				if self.eventType != desiredType:
					continue

			if re.search(matcherStr, matchProp, flags=re.IGNORECASE):
				return True
		return False

	def inWhitelist(self, matchList):

		return self.inMatchlist(matchList, self.name, onNoMatchList=True)

	def inBlacklist(self, matchList):
		return self.inMatchlist(matchList, self.name, onNoMatchList=False)

	def getRawdata(self):
		if self.errorCounter > 0:
			self.rawdata["errorCounter"] = self.errorCounter
		if self.lastErrorDate:
			self.rawdata["lastErrorDate"] = self.lastErrorDate.strftime("%Y-%m-%dT%H:%M:%S")
		return self.rawdata

	def setAsErrored(self):
		self.errored = True

	def incrementErrorCounter(self):
		self.lastErrorDate = datetime.now()
		self.errorCounter += 1

	def isPreventProcessing(self):
		return self.preventProcessing

	def setPreventProcessing(self):
		self.preventProcessing = True

	def process(self, verbose=True):
		try:
			if verbose:
				print
				print "Found %s %s (%s)" % (self.name, self.details, self.eventId)

			if self.isPreventProcessing():
				print "Skipping because of error policy"
				return EventProcessResultType.Skipped

			url = self.getUrl()

			# We check if the URL is a volume for some reason
			if re.match(r"/v/", self.linkFragment):
				#ok what now
				url = None
				volume = self.getVolumeFromUrl()
				if not volume:
					return EventProcessResultType.Error
				
			else:
				#We asume it's a part
				#We check that the part is available FIRST
				try:
					print "Retrieving content..."
					wepubutils.retrieveUrl(url)
				except:
					self.setError("FAILED to retrieve part content")
					return EventProcessResultType.Error

				#We try to get the important values
				volume = self.getVolume()

			# Then we create the config file
			if volume:
				cfgid = volumeNameToConfigFileName(volume["title"])
			else:
				print "Unable to retrieve volume"
				#cfgid = self.toConfigFileName()
				return EventProcessResultType.Error

			self.processedCfgid = cfgid

			cfg = wepubutils.ConfigFile(cfgid)
			cfgdata = cfg.read(verbose=False)

			if not cfgdata:
				cfgdata = {}
				cfgdata["title"] = self.name
				cfgdata["author"] = "Unknown"
				cfgdata["outfile"] = "out/jnc/"+self.toEpubFileName()+".epub"
				cfgdata["urls"] = []

				if volume:
					cfgdata = generateVolumeConfigDict(volume)

					cfgdata["urls"] = getVolumeUrls(volume)
					if url in cfgdata["urls"]:
						cfgdata["urls"].remove(url)

				saved = cfg.write(cfgdata, createNew=True, verbose=False)
				cfgdata = cfg.read(verbose=False)
				if not saved or not cfgdata:
					self.setError("ERROR creating new config")
					return EventProcessResultType.Error

			# Add JNC links to config each time, in case they change
			if volume:
				cfgdata["jncVolumeSlug"] = volume['titleslug']
				
				if 'forumLink' in volume:
					cfgdata["jncForumLink"] = volume['forumLink']
				
				if "totalPartNumber" in volume:
					cfgdata["jncPartNumber"] = volume['totalPartNumber']


			#We add the URL to the config last so that it doesn't stay added in error
			#  when the part isn't available yet


			if not "urls" in cfgdata:
				cfgdata["urls"] = []

			if url:
				if url in cfgdata["urls"]:
					print "Part already exists! Ignoring..."
					if self.errored:
						self.setSuccess()
					return EventProcessResultType.AlreadyProcessed
				cfgdata["urls"].append(url)
				cfgdata["urls"] = sortContentUrlsByPartNumber(cfgdata["urls"])

			if cfg.write(cfgdata, verbose=False):
				pass
			else:
				self.setError("FAILED to add URL to config")
				return EventProcessResultType.Error

			self.setSuccess()

			return EventProcessResultType.Successful
		except Exception, e:
			print
			print "ERROR PROCESSING EVENT"
			print
			print e
			print
			print
			self.setError("EXCEPTION: "+str(e))
			#raise
			return EventProcessResultType.Error

	def setPreventDefaultQueueing(self):
		self.preventDefaultQueueing = True

	def setSuccess(self):
		print "Completed successfully"
		self.rawdata["successDate"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
		if not self.preventDefaultQueueing:
			checkinfo.addSuccessfulEvent(self)
			self.pushoverOk()

	def setError(self, errorMsg):
		print "ERROR:", errorMsg
		self.incrementErrorCounter()
		if not self.preventDefaultQueueing:
			checkinfo.addErroredEvent(self)
			if self.errorCounter == 1:
				self.pushoverError(errorMsg)

	def pushoverOk(self):
		pushover( "[JNC] %s %s" % (self.name, self.details) )

	def pushoverError(self, error="Unknown"):
		pushover( "[JNC][ERROR] %s %s (%s)" % (self.name, self.details, error) )

	def __str__(self):
		return ("[%s] %s - %s" % (utc_to_local(self.date).strftime("%Y-%m-%d %H:%M"), self.name, self.details))

	def isPart(self):
		return (self.eventType == EventType.Part)

	def isFinalPart(self):
		return ((self.eventType == EventType.Part) and self.finalPart)

	def isVolume(self):
		return (self.eventType == EventType.Volume)

	def getUrl(self):
		url = jncapi.Site
		if re.match(u"/", self.linkFragment):
			url += self.linkFragment
		else:
			url += "/"+self.linkFragment
		return url

	def toConfigFileName(self):
		return volumeNameToConfigFileName(self.name)

	def toEpubFileName(self):
		return volumeNameToEpubFilename(self.name)

	def getSlugFromLinkFragment(self):
		x = re.search(r'^/?(c|v|s)/([^/]+)(/.*)?$', self.linkFragment)
		if x:
			return x.group(2)
		else:
			return None


	def getSeries(self):
		if not self.isPart():
			return None

		slug = self.getSlugFromLinkFragment()
		if not slug:
			print "Error extracting slug from linkFragment", self.linkFragment
			return None
		part = jncapi.getPartFromSlug(slug)
		if not part or not "serieId" in part:
			print "Error retrieving event part"
			return None
		series = jncapi.getSeries(part["serieId"])
		
		return series



	def getVolume(self):
		if not self.isPart():
			return None

		slug = self.getSlugFromLinkFragment()
		if not slug:
			print "Error extracting slug from linkFragment", self.linkFragment
			return None
		part = jncapi.getPartFromSlug(slug)
		if not part or not "volumeId" in part:
			print "Error retrieving event part"
			return None
		volume = jncapi.getVolume(part["volumeId"])

		return volume

	def getVolumeFromUrl(self):
		slug = self.getSlugFromLinkFragment()
		if not slug:
			print "Error extracting slug from linkFragment", self.linkFragment
			return None
		return jncapi.getVolumeFromSlug(slug)

	def getPart(self):
		if not self.isPart():
			return None
		slug = self.getSlugFromLinkFragment()
		if not slug:
			print "Error extracting slug from linkFragment", self.linkFragment
			return None
		part = jncapi.getPartFromSlug(slug)
		return part

	def getPartContent(self):
		if not self.isPart():
			return (None, None)
		slug = self.getSlugFromLinkFragment()
		if not slug:
			print "Error extracting slug from linkFragment", self.linkFragment
			return (None, None)
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

def volumeNameToConfigFileName(name):
	n = re.sub(r'[^\d\w]', "_", name)
	n = re.sub(r'_+', '_', n)
	return "jnc_"+n

def volumeNameToEpubFilename(name):
	n = re.sub(r'[^\d\w\.\s\_\-\,\!]', "_", name)
	n = re.sub(r'_+', '_', n)
	return n


def generateVolumeConfigDict(volume):
	cfgdata = {}
	cfgdata["title"] = volume["title"]
	cfgdata["author"] = volume["author"]
	cfgdata["illustrator"] = volume["illustrator"]
	cfgdata["publisher"] = volume["publisherOriginal"]
	cfgdata["cover"] = jncapi.getCoverFullUrlForAttachmentContainer(volume)
	cfgdata["outfile"] = "out/jnc/"+volumeNameToEpubFilename(volume["title"])+".epub"
	cfgdata["urls"] = []

	return cfgdata

def getVolumeUrls(volume):
	urls = []
	for part in volume["parts"]:
		urls.append(jncapi.Site+"/c/"+part["titleslug"])

	return sortContentUrlsByPartNumber(urls)




def printIcal(calendarName, events):

	print "BEGIN:VCALENDAR"
	print "VERSION:2.0"
	print "PRODID:-//hacksw/handcal//NONSGML v1.0//EN"
	print "X-WR-CALNAME:", calendarName

	for event in events:
		print "BEGIN:VEVENT";
		print "UID:", event.eventId
		print "DTSTAMP:", datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
		print "DTSTART:", event.date.strftime("%Y-%m-%dT%H:%M:%SZ")
		print "SUMMARY:", event.name, event.details
		print "END:VEVENT"
	
	print "END:VCALENDAR"


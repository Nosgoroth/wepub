import os, sys, json
import requests
from pprint import pprint
import config

Site = "https://j-novel.club"
Endpoint = "https://api.j-novel.club/api"
Cloudfront = "https://d2dq7ifhe7bu0f.cloudfront.net"

authtoken = None
userid = None

def login():
	global authtoken, userid
	if authtoken:
		return True

	data = request("/Users/login?include=user", data={"email": config.jnc_email, "password": config.jnc_password}, usePost=True)

	try:
		authtoken = data["id"]
		userid = data["user"]["id"]
		return True
	except:
		print("Invalid response when trying to login")
		return False

def request(url, data=None, usePost=False, requireAuth=False, verbose=True):
	global authtoken
	try:
		if requireAuth:
			res = login()
			if not res: return None

		headers = None
		if authtoken:
			#print "USING authtoken:", authtoken
			headers={"Authorization": authtoken}

		# print url, data

		if usePost:
			r = requests.post(Endpoint+url, data=data, headers=headers, timeout=10)
		else:
			r = requests.get(Endpoint+url, data=data, headers=headers, timeout=10)
		
		#print r.text
		json = r.json()

		if "error" in json:
			if verbose:
				print "Error making request to JNC API:"
				try: print "   ", json["error"]["message"]
				except: pass
				print "   ", url
				print "   ", data
			return None
		return json
	except KeyboardInterrupt:
		raise
	except Exception, ex:
		if verbose:
			print "Error making request to JNC API:"
			print "   ", "Error:", ex
			print "   ", url
			print "   ", data
		return None

def getEvent(eventId, verbose=False):
	return request('/events/'+eventId, verbose=verbose)

def getPartFromSlug(slug):
	#https://api.j-novel.club/api/parts/findOne?filter={%22where%22:{%22titleslug%22:%22apparently-it-s-my-fault-that-my-husband-has-the-head-of-a-beast-volume-1-part-1%22},%22include%22:[{%22volume%22:[%22publishInfos%22]}]}
	datafilter = {
		"where": {
			"titleslug": slug
		},
		"include": [
			{
				"volume": ["publishInfos"]
			}
		]
	}
	data = {
		"filter": json.dumps(datafilter)
	}
	return request("/parts/findOne", data=data, requireAuth=True)
	# id, serieid, volumeid


def getPartData(partId):
	#print "getPartData:", partId
	#https://api.j-novel.club/api/parts/5bac40ac45442dd0763fab07/partData
	return request("/parts/%s/partData" % partId, requireAuth=True)


def getPartsLatest():
	#print "getPartData:", partId
	#https://api.j-novel.club/api/parts/5bac40ac45442dd0763fab07/partData
	return request("/parts/", {
		"filter": json.dumps({
			"limit": 10,
			"order": "launchDate DESC"
		})
	})

def getSeries(seriesId):
	datafilter = {
		"where": {
			"id": seriesId
		}
	}
	data = {
		"filter": json.dumps(datafilter)
	}
	return request("/series/findOne", data)

def getSeriesFromSlug(slug):
	datafilter = {
		"where": {
			"titleslug": slug
		},
		"include":[{"volumes": "parts"}]
	}
	data = {
		"filter": json.dumps(datafilter)
	}
	return request("/series/findOne", data)

def getVolume(volumeId):
	datafilter = {
		"where": {
			"id": volumeId
		},
		"include":["parts"]
	}
	data = {
		"filter": json.dumps(datafilter)
	}
	return request("/volumes/findOne", data)

def getVolumeFromSlug(slug):
	datafilter = {
		"where": {
			"titleslug": slug
		},
		"include":["parts"]
	}
	data = {
		"filter": json.dumps(datafilter)
	}
	return request("/volumes/findOne", data)

def getFullUrlFromAttachment(attachment):
	return Cloudfront+"/"+attachment["fullpath"]

def getCoverFullUrlForAttachmentContainer(series):
	try:
		return getFullUrlFromAttachment(series["attachments"][0])
	except:
		return None

def updateReadCompletion(partId, completion=1):
	global userid
	try:
		login()
		if not userid:
			return None
		url = "/users/%s/updateReadCompletion" % userid
		data = {
			"partId": partId,
			"completion": max(0, min(completion, 1)),
		}
		res = request(url, data=data, usePost=True, requireAuth=True, verbose=True)
		return (res != None)
	except:
		raise
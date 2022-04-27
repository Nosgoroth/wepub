import os, sys, json, re
import requests
from pprint import pprint
import config

Site = "https://j-novel.club"
Endpoint = "https://api.j-novel.club/api"
LabsEndpoint = "https://labs.j-novel.club/app/v1"
LabsEmbedEndpoint = "https://labs.j-novel.club/embed"
Cloudfront = "https://d2dq7ifhe7bu0f.cloudfront.net"

authtoken = None
userid = None
authtoken_labs = None


def login(useLabsLogin=False, debug=False):
	if useLabsLogin: return login_labs(debug=debug)

	global authtoken, userid
	if authtoken:
		return True

	data = request("/Users/login?include=user", data={
	               "email": config.jnc_email, "password": config.jnc_password}, usePost=True, debug=debug)

	try:
		authtoken = data["id"]
		userid = data["user"]["id"]
		return True
	except:
		print("Invalid response when trying to login")
		return False


def login_labs(debug=False):
	# https://labs.j-novel.club/app/v1/auth/login
	global authtoken_labs, userid
	if authtoken_labs:
		return True

	data = request("/auth/login?format=json", data={"login": config.jnc_email, "password": config.jnc_password, "slim": True}, usePost=True, endpoint=LabsEndpoint, debug=debug, payloadAsJson=True)


	try:
		authtoken_labs = data["id"]
	except:
		print("Invalid response when trying to login")
		return False

	data = request('/me?format=json', endpoint=LabsEndpoint, debug=debug, requireAuth=True)

	try:
		userid = data["legacyId"]
	except:
		print("Invalid response when trying to login")
		return False

	return True

def request(url, data=None, usePost=False, requireAuth=False, endpoint=None, verbose=True, debug=False, returnText=False, useLabsLogin=False, payloadAsJson=False ):
	global authtoken, authtoken_labs
	try:
		use_authtoken = None

		if not useLabsLogin and endpoint in [LabsEndpoint, LabsEmbedEndpoint]:
			useLabsLogin = True

		if requireAuth:
			if debug: print "Requesting authtoken"
			res = login(useLabsLogin=useLabsLogin)
			if not res:
				if debug: print "Couldn't obtain authtoken"
				return None
			if useLabsLogin:
				use_authtoken = 'Bearer '+authtoken_labs
			else:
				use_authtoken = authtoken

		headers = None
		if use_authtoken:
			if debug: print "USING authtoken:", use_authtoken
			headers = {"Authorization": use_authtoken}

		endpoint = endpoint if endpoint else Endpoint

		if payloadAsJson:
			data = json.dumps(data)
			headers = headers if headers else {}
			headers['Content-Type'] = "application/json"

		if debug:
			print ("POST" if usePost else "GET"), endpoint+url
			if data: print "Payload:", data

		if usePost:
			r = requests.post(endpoint+url, data=data, headers=headers, timeout=10)
		else:
			r = requests.get(endpoint+url, data=data, headers=headers, timeout=10)
		
		if debug:
			print "%d %s" % (r.status_code, r.reason)

		#print r.text
		if returnText:
			return r.text
		
		jsondata = r.json()

		if "error" in jsondata:
			if verbose:
				print "Error making request to JNC API:"
				detailPrinted = False
				try:
					print "   ", jsondata["error"]["message"]
					detailPrinted = True
				except: pass
				if not detailPrinted:
					try:
						print "Raw response text:", r.text
					except: pass
				print "   ", url
				print "   ", data
			return None
		return jsondata
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


OldPartDataContents = "<p><b>You are using an old version of our app that is no longer supported. Please upgrade now to the new J-Novel Club app!</b><p>"

def getPartData(partId, debug=False):
	#print "getPartData:", partId
	
	# The old API endpoint no longer works, it returns:
	#    <p><b>You are using an old version of our app that is no longer supported. Please upgrade now to the new J-Novel Club app!</b><p>
	#https://api.j-novel.club/api/parts/5bac40ac45442dd0763fab07/partData
	#return request("/parts/%s/partData" % partId, requireAuth=True)
	

	return getPartDataLabs(partId, debug=debug)


def getPartDataLabs(partId, debug=False):
	# https://labs.j-novel.club/embed/{part ID}/data.xhtml
	partdata = request("/%s/data.xhtml" % partId, requireAuth=True, endpoint=LabsEmbedEndpoint, debug=debug, returnText=True)
	if not partdata: return None

	m = re.search(r'^.*<body>(.*)</body>.*$', partdata, re.IGNORECASE | re.DOTALL)
	if not m:
		raise Exception("Part format has changed")
	partdata = m.group(1)

	return {
		"dataHTML": partdata
	}


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

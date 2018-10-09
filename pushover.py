import urllib
import urllib2
import urlparse
import json
import os,sys

import config

PUSHOVER_API = "https://api.pushover.net/1/"

class PushoverError(Exception): pass

def pushover(message, token=config.PUSHOVER_TOKEN, user=config.PUSHOVER_USER):
	try:
		if not config.USE_PUSHOVER:
			return

		kwargs = {}
		kwargs['token'] = token
		kwargs['user'] = user
		kwargs['message'] = message
		
		url = urlparse.urljoin(PUSHOVER_API, "messages.json")
		data = urllib.urlencode(kwargs)
		req = urllib2.Request(url, data)
		response = urllib2.urlopen(req)

		output = response.read()
		data = json.loads(output)
		if data['status'] != 1:
			raise PushoverError(output)
		return True
	except PushoverError:
		print "Rejected by Pushover"
		return False
	except:
		print "Pushover error ocurred"
		raise
		return False



def main():
	try:
		pushover(" ".join(sys.argv[1:]))
	except:
		print("An error ocurred.")

if __name__ == "__main__":
    main()
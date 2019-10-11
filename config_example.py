
#Rename this file to config.py



#Your Kindle email address. Amazon will only accept emails originating
# from one of your approved email addresses.
kindle_from = "" 
#The email address of your target Kindle. That device will automatically download
# the book, but it will also be stored in your Kindle personal documents,
# and you can access it from any of your devices.
# If you send a book multiple times, you'll have duplicates! Go to
# amazon.com > "Your content and devices" to delete those dupes.
kindle_to = "???@kindle.com" 

#If you don't want to use Gmail to send mail, edit the code in sendtokindle.py
gmail_user = "????@gmail.com" #Your Gmail user
gmail_pass = "" #An application password

USE_PUSHOVER = False
PUSHOVER_TOKEN = ""
PUSHOVER_USER = ""


wepub_rss_enabled = True
wepub_rss_feeds = [
	{
		"id": "MyRssFeed",
		"url": "https://www.test.dev/rssfeed",
		"config": None,
		"configs": [
			(r'Post name pattern 1', "configName"),
			(r'Post name pattern 2', "otherConfigName"),
		]
	}
]




#Your J-Novel Club email address
jnc_email = "" 
#Your J-Novel Club password
jnc_password = ""

jnc_use_cache = True



jnc_check_whitelist = []
jnc_check_blacklist = []

jnc_calendar_name = "JNC events"
jnc_calendar_whitelist = jnc_check_whitelist
jnc_calendar_blacklist = jnc_check_blacklist

jnc_list_whitelist = jnc_check_whitelist
jnc_list_blacklist = jnc_check_blacklist



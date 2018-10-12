# -*- coding: utf-8 -*-

# Standard modules
import os, sys, re, time, mimetypes, urlparse, zipfile, cgi, hashlib, urllib, json, importlib
# Third party modules
import requests
try:
	from readability.readability import Document
except:
	from readability import Document
from BeautifulSoup import BeautifulSoup,Tag
# App modules
import wepubtemplates
import jncapi

class ConfigFile:
	config = None
	valid = False
	pythonType = False
	readcache = None

	def __init__(self, config):
		self.config = config
		#self.read(verbose=False)

	def existsAsWepubdl(self):
		wepubdlpath = os.path.join("configs", "%s.wepubdl" % self.config)
		return os.path.exists(wepubdlpath)

	def read(self, verbose=True):
		if self.readcache is not None:
			return self.readcache

		wepubdlpath = os.path.join("configs", "%s.wepubdl" % self.config)
		if os.path.exists(wepubdlpath):
			if verbose: print "Using config file", "%s.wepubdl" % self.config

			try:
				with open(wepubdlpath) as f:
					wepubconfig = json.load(f)
			except IOError:
				if verbose: print "No such config:", self.config
				return None
			except ValueError as ex:
				if verbose: 
					print
					print "Syntax error in config", self.config
					print "(Make sure it conforms to strict JSON, not just JS)"
					print
					print ex
				return None

			self.valid = True

			self.readcache = wepubconfig
			return wepubconfig
		else:
			if verbose: print "Using config file", "%s.py" % self.config
			try:
				moduleconfig = importlib.import_module("configs."+self.config)
			except ImportError:
				if verbose: print "No such config:", self.config
				return None
			except SyntaxError:
				if verbose:
					print
					print "Syntax error in config", self.config
					print
				return None
				
			self.pythonType = True
			self.valid = True

			wepubconfig = {}
			for k in [item for item in dir(moduleconfig) if not item.startswith("__")]:
				wepubconfig[k] = moduleconfig.__dict__[k]

			self.readcache = wepubconfig
			return wepubconfig


	def clearReadCache(self):
		self.readcache = None


	def write(self, options, createNew=False, verbose=True):
		if not self.valid and not createNew:
			if verbose: print "Config file is not valid"
			return False

		if self.pythonType:
			if verbose: print "Writing to Python config files not supported"
			return False

		wepubdlpath = os.path.join("configs", "%s.wepubdl" % self.config)
		
		if verbose: print "Using config file", "%s.wepubdl" % self.config

		try:
			with open(wepubdlpath, "w") as f:
				json.dump(options, f, sort_keys=True, indent=4, separators=(',', ': '))
		except IOError:
			if verbose: print "Couldn't write to config:", self.config
			return False

		self.clearReadCache()
		return True

class ObjectDict(object):
    def __init__(self, dictionary):
        for key in dictionary:
            setattr(self, key, dictionary[key])

class EpubProcessor:

	epub = None
	cover = None
	info = None

	def __init__(self, options):

		if type(options) is dict:
			options = ObjectDict(options)

		try: x = options.title_as_header
		except: setattr(options, "title_as_header", True)

		try: x = options.versionid
		except: setattr(options, "versionid", None)

		try: x = options.filters
		except: setattr(options, "filters", [])

		try: x = options.titlefilters
		except: setattr(options, "titlefilters", [])

		try: x = options.nocache
		except: setattr(options, "nocache", False)

		try: x = options.nordbcache
		except: setattr(options, "nordbcache", False)

		try: x = options.preview
		except: setattr(options, "preview", False)

		self.options = options

	def make(self):
		self.processCover()
		self.makeInfo()
		
		# The first file must be named "mimetype"
		self.epub = EpubZipFile(self.options.outfile, 'w', zipfile.ZIP_DEFLATED)
		self.epub.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
		# We need an index file, that lists all other HTML files
		# This index file itself is referenced in the META_INF/container.xml file
		self.epub.writestr("META-INF/container.xml", wepubtemplates.container_tpl)

		self.epub.writestr('OEBPS/cover.html', wepubtemplates.cover_tpl % self.info)
		if self.cover is not None:
			self.epub.write(
				os.path.abspath(self.cover),
				'OEBPS/images/cover'+os.path.splitext(self.cover)[1],
				zipfile.ZIP_DEFLATED
				)


		self.info['manifest'] = ""
		self.info['spine'] = ""
		self.info['toc']= ""

		for i,url in enumerate(self.options.urls):
			(deltamanifest, deltaspine, deltatoc) = self.processUrl(url, i)
			self.info['manifest'] += deltamanifest
			self.info['spine'] += deltaspine
			self.info['toc'] += deltatoc

		# Finally, write the index and toc
		self.epub.writestr('OEBPS/stylesheet.css', wepubtemplates.stylesheet_tpl)
		self.epub.writestr('OEBPS/Content.opf', wepubtemplates.index_tpl % self.info)
		self.epub.writestr('OEBPS/toc.ncx', wepubtemplates.toc_tpl % self.info)

		self.epub.close()


	def makeInfo(self):
		try: isbn = self.options.isbn
		except: isbn = None

		try: description = self.options.description
		except: description = None

		try: title = self.options.title
		except: title = 'Title'

		try: author = self.options.author
		except: author = ''

		if self.cover:
			cpath = 'images/cover' + os.path.splitext(os.path.abspath(self.cover))[1]
			ctype = mimetypes.guess_type(os.path.basename(os.path.abspath(self.cover)))[0]
		else:
			cpath = wepubtemplates.b64emptygif
			ctype = 'image/gif'

		self.info = dict(title=title,
			author=author,
			rights='Copyright respective authors',
			publisher='',
			ISBN=isbn,
			subject='Web content',
			description=description,
			date=time.strftime('%Y-%m-%d'),
			front_cover= cpath,
			front_cover_type = ctype
			)

	def processCover(self):
		try: self.cover = self.options.cover
		except: return False
		if not self.cover: return False

		print "Processing cover...",
		sys.stdout.flush()
		self.cover = processImage(self.cover, ignoreCache=self.options.nocache)
		print "done"

	def processUrl(self, url, index):

		if not url.lower().startswith("http"):
			return self.processStaticPage(url, index)

		print
		print "Reading url no. %s of %s --> %s " % (index+1, len(self.options.urls), url)

		r = retrieveUrl(
			url,
			transforms=self.options.filters,
			titleTransforms=self.options.titlefilters,
			ignoreCache=self.options.nocache,
			ignoreReadability=self.options.nordbcache or self.options.nocache,
			versionId=self.options.versionid
		)

		print "   ", "Retrieved from", r["source"]

		readable_article = r["article"]
		readable_title = r["title"]
		
		if not readable_article:
			print "   ", "No content!!!"
			return ("","","")
		else:
			print "   ", "Content size:", len(readable_article)

		print "   ", "["+readable_title+"]"

		if self.options.preview:
			print readable_article
			sys.exit()

		return self.writePage(readable_article, readable_title, index, baseUrl=url)

	def processStaticPage(self, staticPageStr, index):

		print
		print "Processing static page %s of %s... " % (index+1, len(self.options.urls))

		content = staticPageStr
		title = ''

		r = re.search(r'<title>(.*)</title>', staticPageStr)
		if r:
			title = r.group(1)
			content = content.replace(r.group(0), '')

		content = '<html><head></head><body>%s</body>' % content

		return self.writePage(content, title, index)


	def writePage(self, content, title, index, baseUrl=None):

		manifest = '<item id="article_%s" href="article_%s.html" media-type="application/xhtml+xml"/>\n' % (index+1,index+1)
		spine = '<itemref idref="article_%s" />\n' % (index+1)
		toc = '<navPoint id="navpoint-%s" playOrder="%s"> <navLabel> <text>%s</text> </navLabel> <content src="article_%s.html"/> </navPoint>' % (index+2,index+2,cgi.escape(title),index+1)

		soup = BeautifulSoup(content)
		#Add xml namespace

		soup.html["xmlns"] = "http://www.w3.org/1999/xhtml"

		#Insert header
		body = soup.html.body

		if self.options.title_as_header:
			h1 = Tag(soup, "h1", [("class", "title")])
			h1.insert(0, cgi.escape(title))
			body.insert(0, h1)

		#Add stylesheet path
		head = soup.find('head')
		if head is None:
			head = Tag(soup,"head")
			soup.html.insert(0, head)
		link = Tag(soup, "link", [("type","text/css"),("rel","stylesheet"),("href","stylesheet.css")])
		head.insert(0, link)
		article_title = Tag(soup, "title")
		article_title.insert(0, cgi.escape(title))
		head.insert(1, article_title)

		#Download images
		for j,image in enumerate(soup.findAll("img")):
			#Convert relative urls to absolute urls
			if image["src"].lower().startswith("http"):
				imgfullpath = image["src"]
			elif baseUrl:
				imgfullpath = urlparse.urljoin(baseUrl, image["src"])
			#Remove query strings from url
			imgpath = urlparse.urlunsplit(urlparse.urlsplit(imgfullpath)[:3]+('','',))
			imgfile = os.path.basename(imgpath)
			filename = 'article_%s_image_%s%s' % (index+1,j+1,os.path.splitext(imgfile)[1])

			print "    Processing image: %s %s" % (j+1, imgpath),
			sys.stdout.flush()

			filepath = processImage(imgpath, ignoreCache=self.options.nocache)
			if filepath:
				print "done"

				with open(filepath, "rb") as f:
					content = f.read()
					self.epub.writestr('OEBPS/images/'+filename, content)
				
				image['src'] = 'images/'+filename

				manifest += '<item id="article_%s_image_%s" href="images/%s" media-type="%s"/>\n' % (index+1, j+1, filename, mimetypes.guess_type(filename)[0])
			
			else:
				print "error"


		self.epub.writestr('OEBPS/article_%s.html' % (index+1), str(soup))
		return (manifest, spine, toc)











def processImage(urlOrPath, ignoreCache=False, extension=None): #extension with a dot
	if not urlOrPath: return None
	if not urlOrPath.lower().startswith("http"): return urlOrPath

	if not os.path.isdir("cache"): os.mkdir("cache")

	hashid = hashlib.sha1(urlOrPath).hexdigest()
	if not extension:
		path = urlparse.urlparse(urlOrPath).path
		extension = os.path.splitext(path)[1]
	cachefile = os.path.join("cache", hashid+"_img"+extension)

	if os.path.exists(cachefile):
		return cachefile
	else:
		try:
			r = requests.get(urlOrPath)
			with open(cachefile, 'wb') as f:
				f.write(r.content)
			return cachefile
		except KeyboardInterrupt:
			raise
		except:
			print "Download error"
			return None







class RetrieveUrlException(Exception): pass

def retrieveUrl(url, transforms=[], titleTransforms=[], ignoreCache=False, ignoreReadability=False, versionId=None, setCacheContent=None, setCacheReadable=None, setCacheTitle=None):

	hashsrc = url + (("&v="+str(versionId)) if versionId else "")
	hashid = hashlib.sha1(hashsrc).hexdigest()
	htmlcachefile = os.path.join("cache", hashid+"_raw.html")
	rdbcachefile = os.path.join("cache", hashid+"_rdb.html")
	rdbtcachefile = os.path.join("cache", hashid+"_rdbt.txt")

	if not os.path.isdir("cache"): os.mkdir("cache")

	if setCacheContent:
		with open(htmlcachefile, 'w') as f: f.write(setCacheContent.encode('utf-8'))
	if setCacheReadable:
		with open(rdbcachefile, 'w') as f: f.write(setCacheReadable.encode('utf-8'))
	if setCacheTitle:
		with open(rdbtcachefile, 'w') as f: f.write(setCacheTitle.encode('utf-8'))

	html = None
	rdbhtml = None
	rdbtitle = None
	source = None

	if not os.path.exists(rdbcachefile) or not os.path.exists(rdbtcachefile) or ignoreReadability:
		if not os.path.exists(htmlcachefile) or ignoreCache:
			print "   ", "Getting from network...",
			sys.stdout.flush()

			if "j-novel.club" in url:

				r = re.search(r"\/c\/([^\/]+)\/?(search|read)?$", url)
				if not r:
					raise RetrieveUrlException("Invalid URL for JNC")
				slug = r.group(1)
				part = jncapi.getPartFromSlug(slug)
				if not part or not "id" in part:
					raise RetrieveUrlException("Error retrieving event part")
				partid = part["id"]
				partdata = jncapi.getPartData(partid)
				if not partdata or "dataHTML" not in partdata:
					raise RetrieveUrlException("Error retrieving event part data")

				html = partdata["dataHTML"]
				html = '<html><head></head><body>%s</body>' % html
				rdbhtml = html.encode('utf-8')
				rdbtitle = part["title"].encode('utf-8')


			else:
			
				try:

					#Create a requests session for our cookies in case we need them
					s = requests.Session()

					#Get the URL
					r = s.get(url)

					# If we were redirected to the dumb Tumblr GDPR consent page
					if "tumblr.com" in url and "privacy/consent" in r.url:

						# Get the formkey, if this fails, just let the process die because ¯\_(ツ)_/¯
						privurl = r.url
						m = re.search(r'tumblr_form_key" content\="([^"]+)"', r.text)
						formkey = m.group(1)

						# Mirroring the browser behavior, POST the consent payload with the formkey as a header.
						# This gets us the cookies we need to proceed with our original request.
						# Note: The dumb thing fails if "gdpr_consent_first_party_ads" is false, go figure.
						consentPayload = {
							"eu_resident": True,
							"gdpr_is_acceptable_age": True,
							"gdpr_consent_core": True,
							"gdpr_consent_first_party_ads": True,
							"gdpr_consent_third_party_ads": False,
							"gdpr_consent_search_history": False,
							"redirect_to": url
						}
						headers = {
							"Referer": privurl,
							"Content-Type": "application/json",
							"X-tumblr-form-key": formkey
						}
						r = s.post("https://www.tumblr.com/svc/privacy/consent", headers=headers, data=json.dumps(consentPayload))

						# We perform the original request already
						r = s.get(url)

					print r.status_code

				except:
					print "ERROR"
					raise
				html = r.text

			if not html: raise RetrieveUrlException("Couldn't retrieve URL")

			with open(htmlcachefile, 'w') as f: f.write(html.encode('utf-8'))
			source = "network"
		else:
			with open(htmlcachefile, 'r') as f: html = f.read()
			source = "raw cache"

		if not html: raise RetrieveUrlException("No data")

		if not rdbhtml or not rdbtitle:
			print "   ", "Creating readable version...",
			sys.stdout.flush()
			
			readabilitydoc = Document(html)
			
			rdbhtml = readabilitydoc.summary().encode('utf-8')
			rdbtitle = readabilitydoc.short_title().encode('utf-8')

			print "OK"

		for (rx, to) in transforms:
			try:
				rdbhtml = re.sub(rx.encode('utf-8'), to.encode('utf-8'), rdbhtml)
			except:
				print "   ", "Error with transform", rx, to

		for (rx, to) in titleTransforms:
			try:
				rdbtitle = re.sub(rx.encode('utf-8'), to.encode('utf-8'), rdbtitle)
			except:
				print "   ", "Error with transform", rx, to

		with open(rdbcachefile, 'w') as f: f.write(rdbhtml)
		with open(rdbtcachefile, 'w') as f: f.write(rdbtitle)
	else:
		with open(rdbcachefile, 'r') as f: rdbhtml = f.read()
		with open(rdbtcachefile, 'r') as f: rdbtitle = f.read()
		source = "cache ("+hashid+")"

	if not rdbhtml: raise RetrieveUrlException("No content")

	return {
		"url": url,
		"versionId": versionId,

		"raw": html,
		"article": rdbhtml,
		"title": rdbtitle,

		"rawcachefile": htmlcachefile,
		"articlecachefile": rdbcachefile,
		"titlecachefile": rdbtcachefile,

		"source": source,
	}


class EpubZipFile(zipfile.ZipFile):
	def writestr(self, name, s, compress=zipfile.ZIP_DEFLATED):
		zipinfo = zipfile.ZipInfo(name, time.localtime(time.time())[:6])
		zipinfo.compress_type = compress
		zipfile.ZipFile.writestr(self, zipinfo, s)
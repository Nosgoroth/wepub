#! /usr/bin/python
# -*- coding: utf-8 -*-

import zipfile
import urllib
import sys
import os.path
import mimetypes
import time
import urlparse
import cgi
import re
from pprint import pprint
from optparse import OptionParser
from readability.readability import Document
from BeautifulSoup import BeautifulSoup,Tag
from HTMLParser import HTMLParser
import requests, importlib, hashlib, json
import subprocess

from ebookconvert import convertToFormat, polishepub
import sendtokindle


class MyZipFile(zipfile.ZipFile):
    def writestr(self, name, s, compress=zipfile.ZIP_DEFLATED):
        zipinfo = zipfile.ZipInfo(name, time.localtime(time.time())[:6])
        zipinfo.compress_type = compress
        zipfile.ZipFile.writestr(self, zipinfo, s)


class RetrieveUrlException(Exception): pass

def retrieveUrl(url, transforms=[], titleTransforms=[], ignoreCache=False, ignoreReadability=False, versionId=None):

    hashsrc = url + (("&v="+str(versionId)) if versionId else "")
    hashid = hashlib.sha1(hashsrc).hexdigest()
    htmlcachefile = os.path.join("cache", hashid+"_raw.html")
    rdbcachefile = os.path.join("cache", hashid+"_rdb.html")
    rdbtcachefile = os.path.join("cache", hashid+"_rdbt.txt")

    if not os.path.isdir("cache"): os.mkdir("cache")

    html = None
    rdbhtml = None
    rdbtitle = None
    source = None

    if not os.path.exists(rdbcachefile) or not os.path.exists(rdbtcachefile) or ignoreReadability:
        if not os.path.exists(htmlcachefile) or ignoreCache:
            print "   ", "Getting from network...",
            sys.stdout.flush()
            try:
                r = requests.get(url)
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

        print "   ", "Creating readable version...",
        sys.stdout.flush()
        
        readabilitydoc = Document(html)
        
        rdbhtml = readabilitydoc.summary()
        rdbtitle = readabilitydoc.short_title()

        print "OK"

        for (rx, to) in transforms:
            try:
                rdbhtml = re.sub(rx, to, rdbhtml)
            except:
                print "   ", "Error with transform", rx, to
                pass

        for (rx, to) in titleTransforms:
            try:
                rdbtitle = re.sub(rx, to, rdbtitle)
            except:
                print "   ", "Error with transform", rx, to
                pass

        with open(rdbcachefile, 'w') as f: f.write(rdbhtml.encode('utf-8'))
        with open(rdbtcachefile, 'w') as f: f.write(rdbtitle.encode('utf-8'))
    else:
        with open(rdbcachefile, 'r') as f: rdbhtml = f.read()
        with open(rdbtcachefile, 'r') as f: rdbtitle = f.read()
        source = "cache"

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




def build_command_line():
    parser = OptionParser(usage="Usage: %prog configFile [options]")
    parser.add_option("-r", "--redownload", action="store_true", dest="nocache", help="Don't use cache")
    parser.add_option("--reprocess", action="store_true", dest="nordbcache", help="Use only raw cache")
    parser.add_option("--polish", action="store_true", dest="polish", help="Polishes the resulting epub")
    parser.add_option("--mobi", action="store_true", dest="mobi", help="Convert to MOBI")
    parser.add_option("--kindle", action="store_true", dest="sendtokindle", help="Send to Kindle")
    parser.add_option("-p", "--debug", "--preview", action="store_true", dest="preview", help="Print output of first url and exit")
    return parser


def main():
    parser = build_command_line()
    (options, args) = parser.parse_args()

    if len(args) < 1:
        print "Please specify a config file name"
        sys.exit()

    options.config = args[0]

    try:
        moduleconfig = importlib.import_module("configs."+options.config)
    except:
        print "Invalid config:", options.config
        sys.exit()
    for k in [item for item in dir(moduleconfig) if not item.startswith("__")]:
        v = moduleconfig.__dict__[k]
        #print k, "=", v
        setattr(options, k, v)

    print

    title_as_header = True
    try: title_as_header = options.title_as_header
    except: pass

    cover = None
    try: cover = options.cover
    except: pass

    try: x = options.versionid
    except: setattr(options, "versionid", None)

    try: x = options.filters
    except: setattr(options, "filters", [])
    try: x = options.titlefilters
    except: setattr(options, "titlefilters", [])

    if options.nocache:
        print "Cache will be ignored!"
    if options.nordbcache:
        print "Readability cache will be ignored!"

    nos = len(options.urls)
    cpath = 'data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=='
    ctype = 'image/gif'
    if cover is not None:
        cpath = 'images/cover' + os.path.splitext(os.path.abspath(cover))[1]
        ctype = mimetypes.guess_type(os.path.basename(os.path.abspath(cover)))[0]

    epub = MyZipFile(options.outfile, 'w', zipfile.ZIP_DEFLATED)

    title = 'Title'
    try: title = options.title
    except: pass

    author = ''
    try: author = options.author
    except: pass


    #Metadata about the book
    info = dict(title=title,
            author=author,
            rights='Copyright respective page authors',
            publisher='Rupesh Kumar',
            ISBN='978-1449921880',
            subject='Blogs',
            description='Articles extracted from blogs for archive purposes',
            date=time.strftime('%Y-%m-%d'),
            front_cover= cpath,
            front_cover_type = ctype
            )

    # The first file must be named "mimetype"
    epub.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
    # We need an index file, that lists all other HTML files
    # This index file itself is referenced in the META_INF/container.xml file
    epub.writestr("META-INF/container.xml", '''<container version="1.0"
        xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
        <rootfiles>
            <rootfile full-path="OEBPS/Content.opf" media-type="application/oebps-package+xml"/>
        </rootfiles>
        </container>''')

    # The index file is another XML file, living per convention
    # in OEBPS/content.opf
    index_tpl = '''<package version="2.0"
        xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid">
        <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>%(title)s</dc:title>
        <dc:creator>%(author)s</dc:creator>
        <dc:language>en</dc:language>
        <dc:rights>%(rights)s</dc:rights>
        <dc:publisher>%(publisher)s</dc:publisher>
        <dc:subject>%(subject)s</dc:subject>
        <dc:description>%(description)s</dc:description>
        <dc:date>%(date)s</dc:date>
        <dc:identifier id="bookid">%(ISBN)s</dc:identifier>
        <meta name="cover" content="cover-image" />
        </metadata>
        <manifest>
          <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
          <item id="cover" href="cover.html" media-type="application/xhtml+xml"/>
          <item id="cover-image" href="%(front_cover)s" media-type="%(front_cover_type)s"/>
          <item id="css" href="stylesheet.css" media-type="text/css"/>
            %(manifest)s
        </manifest>
        <spine toc="ncx">
            <itemref idref="cover" linear="no"/>
            %(spine)s
        </spine>
        <guide>
            <reference href="cover.html" type="cover" title="Cover"/>
        </guide>
        </package>'''

    toc_tpl = '''<?xml version='1.0' encoding='utf-8'?>
        <!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"
                 "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
        <ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
        <head>
        <meta name="dtb:uid" content="%(ISBN)s"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
      </head>
      <docTitle>
        <text>%(title)s</text>
      </docTitle>
      <navMap>
        <navPoint id="navpoint-1" playOrder="1"> <navLabel> <text>Cover</text> </navLabel> <content src="cover.html"/> </navPoint>
        %(toc)s
      </navMap>
    </ncx>'''

    cover_tpl = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml">
        <head>
        <title>Cover</title>
        <style type="text/css"> img { max-width: 100%%; } </style>
        </head>
        <body>
        <h1>%(title)s</h1>
        <div id="cover-image">
        <img src="%(front_cover)s" alt="Cover image"/>
        </div>
        </body>
        </html>'''

    stylesheet_tpl = '''
        p, body {
            font-weight: normal;
            font-style: normal;
            font-variant: normal;
            font-size: 1em;
            line-height: 2.0;
            text-align: left;
            margin: 0 0 1em 0;
            orphans: 2;
            widows: 2;
        }
        h2 {
            margin: 5px;
        }
    '''

    manifest = ""
    spine = ""
    toc = ""

    epub.writestr('OEBPS/cover.html', cover_tpl % info)
    if cover is not None:
        epub.write(os.path.abspath(cover),'OEBPS/images/cover'+os.path.splitext(cover)[1],zipfile.ZIP_DEFLATED)


    htmlparser = HTMLParser()

    for i,url in enumerate(options.urls):

        print
        print "Reading url no. %s of %s --> %s " % (i+1,nos,url)

        r = retrieveUrl(
            url,
            transforms=options.filters,
            titleTransforms=options.titlefilters,
            ignoreCache=options.nocache,
            ignoreReadability=options.nordbcache or options.nocache,
            versionId=options.versionid
        )

        print "   ", "Retrieved from", r["source"]

        readable_article = r["article"]
        readable_title = r["title"]
        
        if not readable_article:
            print "   ", "No content!!!"
            continue
        else:
            print "   ", "Content size:", len(readable_article)

        print "   ", "["+readable_title+"]"

        if options.preview:
            print readable_article
            sys.exit()

        manifest += '<item id="article_%s" href="article_%s.html" media-type="application/xhtml+xml"/>\n' % (i+1,i+1)
        spine += '<itemref idref="article_%s" />\n' % (i+1)
        toc += '<navPoint id="navpoint-%s" playOrder="%s"> <navLabel> <text>%s</text> </navLabel> <content src="article_%s.html"/> </navPoint>' % (i+2,i+2,cgi.escape(readable_title),i+1)

        soup = BeautifulSoup(readable_article)
        #Add xml namespace

        soup.html["xmlns"] = "http://www.w3.org/1999/xhtml"

        #Insert header
        body = soup.html.body

        if title_as_header:
            h1 = Tag(soup, "h1", [("class", "title")])
            h1.insert(0, cgi.escape(readable_title))
            body.insert(0, h1)

        #Add stylesheet path
        head = soup.find('head')
        if head is None:
            head = Tag(soup,"head")
            soup.html.insert(0, head)
        link = Tag(soup, "link", [("type","text/css"),("rel","stylesheet"),("href","stylesheet.css")])
        head.insert(0, link)
        article_title = Tag(soup, "title")
        article_title.insert(0, cgi.escape(readable_title))
        head.insert(1, article_title)

        #Download images
        for j,image in enumerate(soup.findAll("img")):
            #Convert relative urls to absolute urls
            imgfullpath = urlparse.urljoin(url, image["src"])
            #Remove query strings from url
            imgpath = urlparse.urlunsplit(urlparse.urlsplit(imgfullpath)[:3]+('','',))
            print "    Downloading image: %s %s" % (j+1, imgpath)
            imgfile = os.path.basename(imgpath)
            filename = 'article_%s_image_%s%s' % (i+1,j+1,os.path.splitext(imgfile)[1])
            if imgpath.lower().startswith("http"):
                epub.writestr('OEBPS/images/'+filename, urllib.urlopen(imgpath).read())
                image['src'] = 'images/'+filename
                manifest += '<item id="article_%s_image_%s" href="images/%s" media-type="%s"/>\n' % (i+1,j+1,filename,mimetypes.guess_type(filename)[0])

        epub.writestr('OEBPS/article_%s.html' % (i+1), str(soup))

    info['manifest'] = manifest
    info['spine'] = spine
    info['toc']= toc

    # Finally, write the index and toc
    epub.writestr('OEBPS/stylesheet.css', stylesheet_tpl)
    epub.writestr('OEBPS/Content.opf', index_tpl % info)
    epub.writestr('OEBPS/toc.ncx', toc_tpl % info)

    print
    print "Wrote epub!"

    if options.polish:
        print
        print "Polishing epub..."
        print
        polishepub(options.outfile)
        print
        print "Polish complete"

    if options.mobi or options.sendtokindle:
        print
        print "Converting to MOBI..."
        print
        retval = convertToFormat(options.outfile, 'mobi')
        print
        print "Conversion completed with exit code", retval

    if options.sendtokindle:
        print
        print "Sending to Kindle, this might take a while...",
        sys.stdout.flush()
        fn, ext = os.path.splitext(options.outfile)
        sendtokindle.sendFromConfig("%s.mobi" % fn)
        print "complete"


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except:
        raise
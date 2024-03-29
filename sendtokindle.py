#! /usr/bin/python
# -*- coding: utf-8 -*-

import os, sys
import smtplib
import mimetypes
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.message import Message
from email.mime.base import MIMEBase
from optparse import OptionParser

import ebookconvert


def sendFromConfig(filepath, extraConvertParams=None, autoConvertMobi=True):
    import config as kindleconfig
    return send(
        filepath,
        fromAddr=kindleconfig.kindle_from,
        toAddr=kindleconfig.kindle_to,
        gmailUser=kindleconfig.gmail_user,
        gmailPass=kindleconfig.gmail_pass,
        extraConvertParams=extraConvertParams,
        autoConvertMobi=autoConvertMobi
    )

def send(filepath, fromAddr=None, toAddr=None, gmailUser=None, gmailPass=None,
    extraConvertParams=None, autoConvertMobi=True):
    fn, ext = os.path.splitext(filepath)

    if not ext == ".mobi" and autoConvertMobi:
    	ebookconvert.convertToFormat(filepath, "mobi", extraParams=extraConvertParams)
    	ext = ".mobi"
    	filepath = fn+ext

    outer = MIMEMultipart()
    outer['Subject'] = 'Kindle document'
    outer['To'] = toAddr
    outer['From'] = fromAddr
    outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'

    fp = open(filepath, 'rb')
    msg = MIMEBase("application", "octet-stream")
    msg.set_payload(fp.read())
    fp.close()
    
    encoders.encode_base64(msg)
    msg.add_header('Content-Disposition', 'attachment', filename="book"+ext)
    outer.attach(msg)
    composed = outer.as_string()

    print "Sending ebook to Kindle via Email..."
    
    s = smtplib.SMTP('smtp.gmail.com:587')
    s.ehlo()
    s.starttls()
    s.login(gmailUser,gmailPass)
    s.sendmail(fromAddr, toAddr, composed)
    s.quit()

    print "Done."

    return True




def build_command_line():
    parser = OptionParser(usage="Usage: %prog file")
    return parser

def main():
    parser = build_command_line()
    parser.add_option("--fix-paragraphs", action="store_true", dest="fixparagraphs", help="Fix paragraph styling when converting to MOBI")
    parser.add_option("--no-convert", action="store_true", dest="noconvert", help="Don't convert to mobi automatically")
    (options, args) = parser.parse_args()

    if len(args) < 1:
        print "Please specify a file"
        sys.exit()

    extraConvertParams = []
    if options.fixparagraphs:
        extraConvertParams += ebookconvert.ConstantFixParagraphOptions

    sendFromConfig(args[0], extraConvertParams=extraConvertParams, autoConvertMobi=(not options.noconvert))

if __name__ == '__main__':
	main()
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

from ebookconvert import convertToFormat


def sendFromConfig(filepath):
    import kindleconfig
    return send(
        filepath,
        fromAddr=kindleconfig.kindle_from,
        toAddr=kindleconfig.kindle_to,
        gmailUser=kindleconfig.gmail_user,
        gmailPass=kindleconfig.gmail_pass
    )

def send(filepath, fromAddr=None, toAddr=None, gmailUser=None, gmailPass=None, autoConvertMobi=True):
    fn, ext = os.path.splitext(filepath)

    if not ext == ".mobi" and autoConvertMobi:
    	convertToFormat(filepath, "mobi")
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
    
    s = smtplib.SMTP('smtp.gmail.com:587')
    s.ehlo()
    s.starttls()
    s.login(gmailUser,gmailPass)
    s.sendmail(fromAddr, toAddr, composed)
    s.quit()

    return True




def build_command_line():
    parser = OptionParser(usage="Usage: %prog file")
    return parser

def main():
    parser = build_command_line()
    (options, args) = parser.parse_args()

    if len(args) < 1:
        print "Please specify a file"
        sys.exit()

    sendFromConfig(args[0])

if __name__ == '__main__':
	main()
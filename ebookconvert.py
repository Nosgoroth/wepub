#! /usr/bin/python
# -*- coding: utf-8 -*-

import os, subprocess


ConstantFixParagraphOptions = [
	"--mobi-ignore-margins",
	"--extra-css",
	"p {margin-top:.4em; margin-bottom:.4em;}"
]


def convertToFormat(path, newext="mobi", extraParams=None):
    (fn, ext) = os.path.splitext(path)
    params = ["ebook-convert", path, fn+"."+newext]
    if extraParams:
    	params += extraParams
    return subprocess.call(params)

def polishepub(path):
    return subprocess.call(["ebook-polish", path, "--smarten-punctuation", "--jacket", "--compress-images"])

def openInEbookViewer(path):
	return subprocess.Popen(["ebook-viewer", path, "--raise-window"])
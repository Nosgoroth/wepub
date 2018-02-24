#! /usr/bin/python
# -*- coding: utf-8 -*-

import os, subprocess

def convertToFormat(path, newext="mobi"):
    (fn, ext) = os.path.splitext(path)
    return subprocess.call(["ebook-convert", path, fn+"."+newext])

def polishepub(path):
    return subprocess.call(["ebook-polish", path, "--smarten-punctuation", "--jacket", "--compress-images"])

def openInEbookViewer(path):
	return subprocess.Popen(["ebook-viewer", path, "--raise-window"])

# wepub

This scripts downloads a series of URLs, strips unnecessary content from them and makes a nice epub/mobi file. It can also send it to your Kindle device.

Heavily based on [web2epub](https://github.com/rupeshk/web2epub) by **rupeshk**, this script adds the following:

* Read book configuration from config files
* Reduced character encoding issues, hopefully
* Cover from URL
* Static HTML chapters
* Caching
* Convert to mobi via Calibre
* Send to Kindle via email

Please do contribute!

## Prerequisites

This script works with Python 2.7.x.

### Packages to install

* [Readability](https://github.com/buriy/python-readability)
* [Requests](http://docs.python-requests.org/en/master/)
* [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/#Download)
* [jstyleson](https://github.com/linjackson78/jstyleson) -- optional, will fallback to built-in `json`, but it's nice to be able to use comments

```bash
pip install readability-lxml requests beautifulsoup4 jstyleson
```

### External binaries

Although it's optional, you may want to install Calibre and [make its CLI binaries available in the path](https://manual.calibre-ebook.com/generated/en/cli-index.html).

Calibre's `ebook-convert`, `ebook-viewer` and `ebook-polish` will be used to enable the functionality of  `--mobi`, `--polish`, `--open` and `--kindle`. You can still create epubs without it.

## Making an ebook

So, you have a bunch of URLs, maybe chapters in a web novel, that you'd like to convert to epub to, for example, read in your e-reader. Let's do it!

### Create a config

1. Create a config `.wepubdl` (JSON) or `.py` (Python module) file in the `configs` folder, named as you like. You can copy the provided `example.py` or `example.wepubdl`. If distributing configs, it's safer to stick to the `.wepubdl` ones.
2. Set at least `title`, `author` and `outfile`. The path for `outfile` is relative to the root of the project, not the config file.
3.  Set the `urls` array. Each URL will become a chapter. See the section below on how to add static chapters.
4. If you have a cover image, set `cover` to the relative path of the image, or an URL.
5. Consider adding filters to the body (`filters`) and the title (`titlefilters`). These are tuples where the first and second elements will be passed as parameters to `re.sub`. If using `.wepubdl`, escape the escape characters!
6. You can decide if you want to add the html page title as a header for the chapter by setting `title_as_header`. It defaults to `True`.

It should look like this for `.wepubdl` configs:

```js
{
    "title": "My test ebook",
    "author": "Various Wikipedia collaborators",
    "outfile": "out/My test ebook.epub",
    //"cover": "covers/some_image.jpg", //can also be an URL
    "title_as_header": true,
    "urls": [
        "https://en.wikipedia.org/wiki/E-book",
        "https://en.wikipedia.org/wiki/Python_(programming_language)",
        "https://en.wikipedia.org/wiki/Initial_mass_function",
        "https://en.wikipedia.org/wiki/Airport_and_airline_management",
    ],
    "filters": [
        [ "<a[^\\>]+>(.*?)</a>", "\\1" ],
        [ "\\[[^\\]]*\\]", "" ],
    ],
    "titlefilters": [
        [ "Airport", "Starbase" ]
    ],
}
```

(Note that to use `.wepubdl` configs with comments or trailing commas, you need to install the `jstyleson` Python package.)

Or like this for `.py` configs:

```py
# -*- coding: utf-8 -*-

title = "My test ebook"
author = "Various Wikipedia collaborators"
outfile = "out/My test ebook.epub"
cover = "covers/some_image.jpg" #can also be a url
title_as_header = True
urls = [
    "https://en.wikipedia.org/wiki/E-book",
    "https://en.wikipedia.org/wiki/Python_(programming_language)",
    "https://en.wikipedia.org/wiki/Initial_mass_function",
    "https://en.wikipedia.org/wiki/Airport_and_airline_management"
]
filters = [
    [ r'<a[^\>]+>(.*?)</a>', r'\1' ], #removes links but keeps the text inside
    [ r'\[[^\]]*\]', r'' ]  #removes stuff within brackets
]
titlefilters = [
    [ r'Airport', r'Starbase' ]
]
```


#### Static chapters

You can add static chapters by including HTML as a string in the `urls` array. You can define the chapter title by including a `<title>` element somewhere within the string.

A `.py` config example:

```py
urls = [
    '''
        <title>A leading test image</title>
        <p><img src="https://i.imgur.com/ciWcTlk.jpg" /></p>
        <p>What did you expect?</p>
    ''',
    "https://en.wikipedia.org/wiki/E-book",
    "https://en.wikipedia.org/wiki/Python_(programming_language)",
    #...
]
```

Note that in `.wepubdl` configs, which are JSON files, you can't use multiline strings:

```js
"urls": [
    "<title>A leading test image</title><p><img src=\"https://i.imgur.com/ciWcTlk.jpg\" /></p><p>What did you expect?</p>'",
    "https://en.wikipedia.org/wiki/E-book",
    "https://en.wikipedia.org/wiki/Python_(programming_language)",
    //...
],
```

### Run it

You can now run this config, which we'll imagine you named `myconfig.wepubdl` or `myconfig.py`, by going down to the root folder of the project and running:

```bash
python wepub.py myconfig
```

If both a `.wepubdl` config and an `.py` config exist, the `.wepubdl` config will be used.


#### Extra options

There are options that you can consult with `--help`, and they include these:

* `--redownload`: Ignores all the cache (documents and images)
* `--reprocess`: Respects the download cache but reprocesses the readability and filter passes. If you don't use it you can modify the cache files manually.
* `--preview`: Prints to stdout the processed contents of first chapter and exits.
* `--open`: Opens the resulting epub in Calibre's `ebook-viewer`
* `--mobi`: Converts the result to mobi.
* `--kindle`: Sends the result to Kindle. See its section.

You can also set these switches as variables in your config:

* `nocache` for `--redownload`
* `nordbcache` for `--reprocess`
* `preview` for `--preview`
* `mobi` for `--mobi`
* `sendtokindle` for `--kindle`

## Send to Kindle

Directly send to Kindle with this script.

### Credentials

Create a `kindleconfig.py` file. You can just rename the `kindleconfig_example.py` file provided. Fill it with your credentials and email addresses as specified.

If you want to use a different SMTP server that's not Gmail, you'll have to code it in `sendtokindle.py`.

### Usage

You can send to Kindle by using the `--kindle` switch in `wepub.py`:

```bash
python wepub.py myconfig --kindle
```

You can also use this functionality completely separate from `wepub.py`:

```bash
python sendtokindle.py ~/myebook.mobi
```

If it's not a mobi file the script will attempt to convert it. You will need Calibre installed for this to work:

```bash
python sendtokindle.py ~/myebook.epub
```

## Known snags

* `ebook-polish` doesn't handle file names properly.
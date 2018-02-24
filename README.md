
# wepub documentation

Heavily based on [web2epub](https://github.com/rupeshk/web2epub) by **rupeshk**, this script adds the following:

* Caching
* Hopefully reduced character encoding issues
* Read book configuration from config files
* Converting to mobi via Calibre
* Sending to Kindle

## Prerequisites

* Python 2.7.x
* Python packages: `readability`, `requests`, `BeautifulSoup`
* External binaries: Calibre's `ebook-convert`, `ebook-viewer` and `ebook-polish`, in the path. You can continue without this, but you won't be able to use `--mobi`, `--polish`, `--open` or `--kindle`.
* Some patience if bugs crop up

## Downloading from the web

1. Create a config `.py` file in the configs folder, named as you like. You can copy the provided `example.py`.
2. Set at least the `title`, `author` and `outfile` variables. The path for `outfile` is relative to the root of the project, not the config file.
3.  Set the `urls` array. Each URL will become a chapter. See the section below on how to add static chapters.
4. If you have a cover image, set the `cover` variable to the relative path of the image, or an URL.
5. Consider adding filters to the body (`filters`) and the title (`titlefilters`). These are tuples where the first and second elements will be passed as parameters to `re.sub`
6. You can decide if you want to add the html page title as a header for the chapter by setting `title_as_header`. It defaults to `True`.

It should look like this:

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

You can now run this config, which we'll imagine you named `myconfig.py`, by going down to the root folder of the project and running:

```bash
python wepub.py myconfig
```

### Static chapters

You can add static chapters by including HTML as a string in the `urls` array. You can define the chapter title by including a `<title>` element somewhere within the string.

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



### Extra options

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

## Sending to Kindle

Create a `kindleconfig.py` file. You can just rename the `kindleconfig_example.py` file provided. Fill it with your credentials and email addresses as specified.

If you want to use a different SMTP server that's not Gmail, you'll have to code it in `sendtokindle.py`.

You can send to kindle by using the `--kindle` switch in `wepub.py`, or you can send a file directly:

```bash
python sendtokindle.py out/myebook.epub
```

If it's not a mobi file the script will attempt to convert it. You can use this functionality completely separate from `wepub.py`.

## Known snags

* `ebook-polish` doesn't handle file names properly.

# wepub

This scripts downloads a series of URLs, strips unnecessary content from them and makes a nice epub/mobi file. It can also send it to your Kindle device.

Originally based on [web2epub](https://github.com/rupeshk/web2epub) by **rupeshk**, this script adds the following:

* Read book configuration from config files
* Reduced character encoding issues, hopefully
* Cover from URL
* Static HTML chapters
* Caching
* Convert to mobi via Calibre
* Send to Kindle via email
* J-Novel Club support

This code is provided as-is. If you encounter an issue, please file it in Github, but I might not have the time to fix it myself. Please do contribute!

## Prerequisites

This script works with Python 2.7.x because I'm stubborn and bad with change.

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

Create a `config.py` file. You can just rename the `config_example.py` file provided. Fill it with your credentials and email addresses as specified.

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

If, when converting to mobi, you get odd looking paragraphs, you might want to use the `--fix-paragraphs` option. You can use this option in both `wepub.py` and `sendtokindle.py`.

## J-Novel Club support

[J-Novel Club](https://j-novel.club/howitworks) (JNC) is a light novel translation and publishing company that allows members to read weekly parts of a volume as it's translated before its final release as an epub in the usual stores. The JNC integration takes two forms:

* Support for JNC part URLs in wepub configs
* A `jnc.py` script that can create and modify wepub configs based on different events

Both require a JNC account with a paid membership in order to access all available parts -- otherwise, you will only be able to access parts available to free members, which are usually only the first part of a volume.

This script uses JNC's undocumented API that powers both their website and their app -- both of which kind of suck at the time of writing, so you can generate epubs with this and read them in a better reader.

### Authentication

Simply fill in the variables in `config.py`:

```py
#Your J-Novel Club email address
jnc_email = "" 
#Your J-Novel Club password
jnc_password = ""
```

### JNC part URLs in wepub configs

There's no mystery here: add a URL to a wepub config and run it.

```js
{
    "title": "Realist Hero Vol. 1",
    "author": "Dojyomaru",
    "outfile": "out/realist_hero_1.epub",
    "urls": [
        "https://j-novel.club/c/how-a-realist-hero-rebuilt-the-kingdom-volume-1-part-1"
    ]
}
```

### The jnc.py script

This script can be called from the command line, same as `wepub.py`. Its functionality is described below:

#### Important: about events

Events are JNC releases, and can be parts or ebook volumes. This script only deals in part releases.

By default the script requests 25 events. You can change this behavior with the `--limit` parameter.

```bash
python jnc.py --limit 5
```

#### Important: about the cache

The script will aggresively cache its calls to retrieve the events list, even when search parameters are different. If you have performed a custom request, for example with a different result limit, be sure to append `--nocache` to the next request so that the previous cached request isn't used. By default, the cache's TTL is 60 minutes.

```bash
python jnc.py --nocache
```

#### Print the latest events

Prints the latest events in the console. 

```bash
python jnc.py
```

#### Print upcoming events

Prints the next upcoming events in the console.

```bash
python jnc.py --next
```

#### Check events and generate configs

Checks the latest events and adds the relevant parts to the corresponding volume configs. If the configs don't exist, it creates them and prefills them with any previous parts. Then, it generates epubs for the modified/created configs.

After the executions ends, the script will remember the date of the latest successfully processed event so that they aren't processed again. Additionally, if a part download fails (maybe because it's not available yet despite the event date), it will remember it to test it in the next run. In order to reset this memory, use the `--cleardata` option.

```bash
python jnc.py --check
```

#### Download a volume or a whole series

Useful for monthly catchups. Simply provide the volume URL after the `--genvolume` option, or the series URL after the `--genseries` option.

```bash
python jnc.py --genvolume https://j-novel.club/v/how-a-realist-hero-rebuilt-the-kingdom-volume-1/
```

```bash
python jnc.py --genseries https://j-novel.club/s/how-a-realist-hero-rebuilt-the-kingdom/
```

### Notifications

The JNC script integrates [Pushover](https://pushover.net), a paid (one-time fee) service for custom notifications. In order to use it, login into their website with your account, generate a new Pushover application (or use an existing one), grab the user key and application API token, and paste them in `config.py`:

```py
USE_PUSHOVER = True
PUSHOVER_TOKEN = "123456789012345678901234567890"
PUSHOVER_USER = "qwertyuiopasdfghjklzxcvbnm"
```

(Don't forget to change `USE_PUSHOVER` to `True`!)

By doing this, you will receive a notification in your devices where you have installed the Pushover app whenever a part is downloaded or an error happens.

### Tips and tricks

You could use a cronjob (or any other way of running a script periodically) to make `jnc.py` check for released parts and generate the corresponding epubs. Additionally, you could symlink the `out` folder to a netwoerk-available location (like Dropbox) to make these epubs available to ebook readers that support network locations.



## Known snags

* `ebook-polish` doesn't handle file names properly.
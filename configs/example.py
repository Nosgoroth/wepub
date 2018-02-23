title = "My test ebook"
author = "Various Wikipedia collaborators"
outfile = "out/My test ebook.epub"

#cover = "covers/some_image.jpg"

title_as_header = True

urls = [
	"https://en.wikipedia.org/wiki/E-book",
	"https://en.wikipedia.org/wiki/Python_(programming_language)",
	"https://en.wikipedia.org/wiki/Initial_mass_function",
	"https://en.wikipedia.org/wiki/Airport_and_airline_management"
]

filters = [
	[ r'<a[^\>]+>(.*?)</a>', r'\1' ],
	[ r'\[[^\]]*\]', r'' ]
]

titlefilters = [
	[ r'Airport', r'Starbase' ]
]
#!/Library/Frameworks/Python.framework/Versions/3.7/bin/python3
# -*- coding: utf-8 -*-

use_urllib = False

import os
import sys
import re
if use_urllib:
	import urllib.request
else:
	import subprocess
import bs4

def print_card_for_URL(src_URL, css_class_prefix='card', default_image_URL=None):
	if use_urllib:
		response = urllib.request.urlopen(src_URL)
		if response.getcode() != 200:
			print('error fetching %s: response was error %u' % (src_URL, response.getcode()), file=sys.stderr)
			return
	else:
		curl_output_separator='\n---CARD_FETCHER_CURL_OUTPUT_SEPARATOR---\n'
		curl = subprocess.Popen([ 'curl', '-L', '--write-out', curl_output_separator + '%{response_code}', src_URL ], stdout=subprocess.PIPE)
		response = curl.stdout.read()
		response, curl_output = response.split(curl_output_separator.encode('utf-8'))
		if curl.wait() != 0:
			response_code = int(curl_output)
			print('error fetching %s: response was error %u' % (src_URL, response_code), file=sys.stderr)
			return
		
#	data = response.read()
#	import subprocess; subprocess.Popen([ 'head', '-n', '20' ], stdin=subprocess.PIPE).stdin.write(data)
	soup = bs4.BeautifulSoup(response, 'html.parser')
	def get_meta_property(property_name):
		meta = soup.find('meta', attrs={ 'property': property_name })
		return meta['content'] if meta else None
	title_str = get_meta_property('og:title')
	image_str = get_meta_property('og:image')
	description_str = get_meta_property('og:description')
	author_str = get_meta_property('og:author')
	url_str = get_meta_property('og:url')

	cursor = object()
	lines = [
		'<div class="CARDCSSCLASSPREFIX' + (' CARDCSSCLASSPREFIX_with_image' if (image_str or default_image_URL) else '') + '">',
		cursor,
		'</div>',
	]
	if image_str or default_image_URL:
		lines.insert(lines.index(cursor), '<div class="CARDCSSCLASSPREFIX_thumbnail"><img src="{image_URL}" class="CARDCSSCLASSPREFIX_thumbnail_value" /></div>'.format(image_URL=image_str or default_image_URL))
	lines.insert(lines.index(cursor), '<div class="CARDCSSCLASSPREFIX_text">')
	lines.insert(lines.index(cursor) + 1, '</div>')

	if title_str:
		lines.insert(lines.index(cursor), '<p style="font-weight: bold" style="CARDCSSCLASSPREFIX_title"><span class="CARDCSSCLASSPREFIX_title_value"><a href="{link_URL}">{title}</a></span></p>'.format(link_URL=url_str or src_URL, title=title_str))
	if author_str:
		lines.insert(lines.index(cursor), '<p style="CARDCSSCLASSPREFIX_author"><span class="CARDCSSCLASSPREFIX_author_value">{author}</span></p>'.format(author=author_str))
	if description_str:
		lines.insert(lines.index(cursor), '<p style="CARDCSSCLASSPREFIX_description"><span class="CARDCSSCLASSPREFIX_description_value">{description}</span></p>'.format(description=description_str))
	lines.remove(cursor)

	for x in lines: print(x.replace('CARDCSSCLASSPREFIX', css_class_prefix))

stylesheet = '''\
<style type="text/css">
div.CARDCSSCLASSPREFIX {
	border: 1pt solid gray;
	border-radius: 5pt;
	max-width: 300pt;
	font-family: "Roboto", "Helvetica", "Arial", sans-serif;
}
div.CARDCSSCLASSPREFIX.CARDCSSCLASSPREFIX_with_image {
	display: grid;
	grid-template-columns: 1fr 2fr;
}
div.CARDCSSCLASSPREFIX div.CARDCSSCLASSPREFIX_thumbnail {
	padding: 5pt;
}
div.CARDCSSCLASSPREFIX div.CARDCSSCLASSPREFIX_thumbnail img.CARDCSSCLASSPREFIX_thumbnail_value {
	width: 100pt;
	max-height: 100%;
}
div.CARDCSSCLASSPREFIX div.CARDCSSCLASSPREFIX_text span.CARDCSSCLASSPREFIX_title_value {
	font-family: "Roboto Slab", "Helvetica", "Arial", sans-serif;
}
div.CARDCSSCLASSPREFIX div.CARDCSSCLASSPREFIX_text span.CARDCSSCLASSPREFIX_author_value:before {
	content: 'by ';
}
</style>
'''

if __name__ == '__main__':
	import fileinput
	import argparse

	parser = argparse.ArgumentParser(description='Print HTML source for a “card” representation of the resource at a URL. Can be used on multiple URLs, and multiple such cards will be printed.')
	parser.add_argument('-F', '--read-from', dest='input_paths', metavar='path', action='append', help='File to read URLs from, one per line (- for stdin)')
	parser.add_argument('--css-class-prefix', default='card', help='Use this prefix on all CSS classes applied to the generated cards')
	parser.add_argument('--default-image', dest='default_image_URL', metavar='URL', help='Use this thumbnail for resources that don\'t have an og:image')
	parser.add_argument('input_URLs', metavar='URL', nargs='*', help='URLs to generate cards for')
	opts = parser.parse_args()

	if not (opts.input_paths or opts.input_URLs):
		parser.error('No URLs provided')

	print('<div>')
	print(stylesheet.replace('CARDCSSCLASSPREFIX', opts.css_class_prefix))
	if opts.input_paths:
		for line in fileinput.input(opts.input_paths):
			URL = line.strip()
			print_card_for_URL(URL, css_class_prefix=opts.css_class_prefix, default_image_URL=opts.default_image_URL)
	for URL in opts.input_URLs:
		print_card_for_URL(URL, css_class_prefix=opts.css_class_prefix, default_image_URL=opts.default_image_URL)
	print('</div>')

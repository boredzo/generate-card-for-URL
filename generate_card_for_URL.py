#!/Library/Frameworks/Python.framework/Versions/3.7/bin/python3
# -*- coding: utf-8 -*-

use_urllib = False

import os
import sys
import re
import time
import pathlib
import csv
if use_urllib:
	import urllib.request
else:
	import subprocess
import bs4

class ResourceCache(object):
	def __init__(self):
		self.cache_dir_path = pathlib.Path('~/.generate_card_for_URL').expanduser()
		try: os.mkdir(self.cache_dir_path)
		except FileExistsError: pass

		self.csv_file_path = self.cache_dir_path.joinpath('URLs.csv')
		if not self.csv_file_path.exists():
			with open(self.csv_file_path, 'w') as f:
				writer = csv.writer(f)
				writer.writerow([ 'source_URL', 'og:url', 'og:title', 'og:author', 'og:image', 'og:description' ])

		self._cache = {}
		with open(self.csv_file_path, 'r') as f:
			reader = csv.reader(f)
			for row in reader:
				cached_src_URL = row[0]
				self._cache[cached_src_URL] = row


	def add(self, src_URL, meta_URL, title, author, image, description):
		assert src_URL, 'source URL is a required argument; must be a string, not None'
		with open(self.csv_file_path, 'a') as f:
			writer = csv.writer(f)
			writer.writerow([ src_URL, meta_URL or '', title or '', author or '', image or '', description or '' ])

	def __getitem__(self, src_URL):
		return self._cache[src_URL]

def print_card_for_URL(src_URL, css_class_prefix='card', default_image_URL=None, delay_after_fetch=0, verbose=False, _cache=ResourceCache()):
	fetched_remotely = False
	try:
		cached_src_URL, url_str, title_str, author_str, image_str, description_str = _cache[src_URL]
	except KeyError:
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

		fetched_remotely = True

		soup = bs4.BeautifulSoup(response, 'html.parser')
		def get_meta_property(property_name):
			meta = soup.find('meta', attrs={ 'property': property_name })
			return meta['content'] if meta else None
		title_str = get_meta_property('og:title')
		image_str = get_meta_property('og:image')
		description_str = get_meta_property('og:description')
		author_str = get_meta_property('og:author')
		url_str = get_meta_property('og:url')

		_cache.add(src_URL, url_str, title_str, author_str, image_str, description_str)
	else:
		if verbose:
			print('Cache hit!', file=sys.stderr)

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
	sys.stdout.flush()

	if fetched_remotely: time.sleep(delay_after_fetch)

stylesheet = '''\
<style type="text/css">
div.CARDCSSCLASSPREFIX {
	border: 1pt solid gray;
	border-radius: 5pt;
	max-width: 300pt;
	font-family: "Roboto", "Helvetica", "Arial", sans-serif;
	margin-bottom: 5pt;
	margin-left: auto;
    margin-right: auto;
    padding: 5pt;
}
div.CARDCSSCLASSPREFIX.CARDCSSCLASSPREFIX_with_image {
	display: grid;
	grid-template-columns: 1fr 2fr;
}
div.CARDCSSCLASSPREFIX div.CARDCSSCLASSPREFIX_thumbnail {
	margin-right: 5pt;
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
	parser.add_argument('--delay-after-fetch', metavar='seconds', default=0, type=float, help='Wait this many seconds after each remote fetch (to avoid arousing the ire of server admins)')
	parser.add_argument('--verbose', action='store_true', default=False, help='Print more information about what the tool is or is not doing')
	parser.add_argument('input_URLs', metavar='URL', nargs='*', help='URLs to generate cards for')
	opts = parser.parse_args()

	if not (opts.input_paths or opts.input_URLs):
		parser.error('No URLs provided')

	print('<div>')
	print(stylesheet.replace('CARDCSSCLASSPREFIX', opts.css_class_prefix))
	if opts.input_paths:
		for line in fileinput.input(opts.input_paths):
			URL = line.strip()
			print_card_for_URL(URL, css_class_prefix=opts.css_class_prefix, default_image_URL=opts.default_image_URL, delay_after_fetch=opts.delay_after_fetch, verbose=opts.verbose)
	for URL in opts.input_URLs:
		print_card_for_URL(URL, css_class_prefix=opts.css_class_prefix, default_image_URL=opts.default_image_URL, delay_after_fetch=opts.delay_after_fetch, verbose=opts.verbose)
	print('</div>')

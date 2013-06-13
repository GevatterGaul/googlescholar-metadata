#! /usr/bin/env python
"""
This module provides classes for querying Google Scholar and parsing
returned results.  It currently *only* processes the first results
page.  It is not a recursive crawler.
"""
# Version: 1.5 -- $Date: 2012-09-27 10:44:39 -0700 (Thu, 27 Sep 2012) $
#
# ChangeLog
# ---------
#
# 1.6:  Added bibtex output, by Benjamin Behringer <mail at benjamin-behringer.de>
#
# 1.5:  A few changes:
#
#       - Tweak suggested by Tobias Isenberg: use unicode during CSV
#         formatting.
#
#       - The option -c|--count now understands numbers up to 100 as
#         well. Likewise suggested by Tobias.
#
#       - By default, text rendering mode is now active. This avoids
#         confusion when playing with the script, as it used to report
#         nothing when the user didn't select an explicit output mode.
#
# 1.4:  Updates to reflect changes in Scholar's page rendering,
#       contributed by Amanda Hay at Tufts -- thanks!
#
# 1.3:  Updates to reflect changes in Scholar's page rendering.
#
# 1.2:  Minor tweaks, mostly thanks to helpful feedback from Dan Bolser.
#       Thanks Dan!
#
# 1.1:  Made author field explicit, added --author option.
#
# pylint: disable-msg=C0111
#
# Copyright 2010--2012 Christian Kreibich. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#    1. Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import optparse
import sys
import re
import urllib
import urllib2
from cookielib import CookieJar
from BeautifulSoup import BeautifulSoup

class Article():
    """
    A class representing articles listed on Google Scholar.  The class
    provides basic dictionary-like behavior.
    """
    def __init__(self):
        self.attrs = {'title':         [None, 'Title',          0],
                      'url':           [None, 'URL',            1],
                      'num_citations': [0,    'Citations',      2],
                      'num_versions':  [0,    'Versions',       3],
                      'url_citations': [None, 'Citations list', 4],
                      'url_versions':  [None, 'Versions list',  5],
                      'bibtex_id':     [None, 'Bibtex ID',      6],
                      'year':          [None, 'Year',           7]}

    def __getitem__(self, key):
        if key in self.attrs:
            return self.attrs[key][0]
        return None

    def __setitem__(self, key, item):
        if key in self.attrs:
            self.attrs[key][0] = item
        else:
            self.attrs[key] = [item, key, len(self.attrs)]

    def __delitem__(self, key):
        if key in self.attrs:
            del self.attrs[key]

    def as_txt(self):
        # Get items sorted in specified order:
        items = sorted(self.attrs.values(), key=lambda item: item[2])
        # Find largest label length:
        max_label_len = max([len(str(item[1])) for item in items])
        fmt = '%%%ds %%s' % max_label_len
        return '\n'.join([fmt % (item[1], item[0]) for item in items])

    def as_csv(self, header=False, sep='|'):
        # Get keys sorted in specified order:
        keys = [pair[0] for pair in \
                    sorted([(key, val[2]) for key, val in self.attrs.items()],
                           key=lambda pair: pair[1])]
        res = []
        if header:
            res.append(sep.join(keys))
        res.append(sep.join([unicode(self.attrs[key][0]) for key in keys]))
        return '\n'.join(res)

    def as_bib(self):
        """ Print only the bibtex output, ignore other collected information """
        return getattr(self, 'bibtex_string', '')


class ScholarParser():
    """
    ScholarParser can parse HTML document strings obtained from Google
    Scholar. It invokes the handle_article() callback on each article
    that was parsed successfully.
    """
    SCHOLAR_SITE = 'http://scholar.google.com'

    def __init__(self, site=None):
        self.soup = None
        self.article = None
        self.site = site or self.SCHOLAR_SITE
        self.year_re = re.compile(r'\b(?:20|19)\d{2}\b')

    def handle_article(self, art):
        """
        In this base class, the callback does nothing.
        """

    def parse(self, html):
        """
        This method initiates parsing of HTML content.
        """
        self.soup = BeautifulSoup(html)
        for div in self.soup.findAll(ScholarParser._tag_checker):
            self._parse_article(div)

    def parse_bibtex_link(self, html):
        """
        Extract the bibtex link from the AJAX page presented by google.

        Returns the bibtex link.
        """
        self.soup = BeautifulSoup(html)
        for a in self.soup.findAll('a'):
            if a.get('href').startswith('/scholar.bib'):
                return a.get('href')

        return None

    def parse_bibtex_entry(self, bibtex):
        """ Parse a bibtex entry to a dict """
        pass

    def _parse_article(self, div):
        self.article = Article()

        for tag in div:
            if not hasattr(tag, 'name'):
                continue

            if tag.name == 'div' and tag.get('class') == 'gs_rt' and \
                    tag.h3 and tag.h3.a:
                self.article['title'] = ''.join(tag.h3.a.findAll(text=True))
                self.article['url'] = self._path2url(tag.h3.a['href'])

            if tag.name == 'font':
                for tag2 in tag:
                    if not hasattr(tag2, 'name'):
                        continue
                    if tag2.name == 'span' and tag2.get('class') == 'gs_fl':
                        self._parse_links(tag2)

        if self.article['title']:
            self.handle_article(self.article)

    def _parse_links(self, span):
        for tag in span:
            if not hasattr(tag, 'name'):
                continue
            if tag.name != 'a' or (tag.get('href') == None and tag.get('a') == None):
                continue

            if not tag.get('href') is None:
                if tag.get('href').startswith('/scholar?cites'):
                    if hasattr(tag, 'string') and tag.string.startswith('Cited by'):
                        self.article['num_citations'] = \
                            self._as_int(tag.string.split()[-1])
                    self.article['url_citations'] = self._path2url(tag.get('href'))

                if tag.get('href').startswith('/scholar?cluster'):
                    if hasattr(tag, 'string') and tag.string.startswith('All '):
                        self.article['num_versions'] = \
                            self._as_int(tag.string.split()[1])
                    self.article['url_versions'] = self._path2url(tag.get('href'))

            if not tag.get('onclick') is None:
                if tag.get('onclick').startswith('return gs_ocit'):
                    ref_id = re.search(".*event,'([\w-]+)'", tag.get('onclick')).group(1)
                    self.article['bibtex_id'] = ref_id

    @staticmethod
    def _tag_checker(tag):
        if tag.name == 'div' and tag.get('class') == 'gs_r':
            return True
        return False

    def _as_int(self, obj):
        try:
            return int(obj)
        except ValueError:
            return None

    def _path2url(self, path):
        if path.startswith('http://'):
            return path
        if not path.startswith('/'):
            path = '/' + path
        return self.site + path

class ScholarParser120201(ScholarParser):
    """
    This class reflects update to the Scholar results page layout that
    Google recently.
    """

    def _parse_article(self, div):
        self.article = Article()

        for tag in div:
            if not hasattr(tag, 'name'):
                continue

            if tag.name == 'h3' and tag.get('class') == 'gs_rt' and tag.a:
                self.article['title'] = ''.join(tag.a.findAll(text=True))
                self.article['url'] = self._path2url(tag.a['href'])

            if tag.name == 'div' and tag.get('class') == 'gs_a':
                year = self.year_re.findall(tag.text)
                self.article['year'] = year[0] if len(year) > 0 else None

            if tag.name == 'div' and tag.get('class') == 'gs_fl':
                self._parse_links(tag)

        if self.article['title']:
            self.handle_article(self.article)

class ScholarParser120726(ScholarParser):
    """
    This class reflects update to the Scholar results page layout that
    Google made 07/26/12.
    """

    def _parse_article(self, div):
        self.article = Article()

        for tag in div:
            if not hasattr(tag, 'name'):
                continue

            if tag.name == 'div' and tag.get('class') == 'gs_ri':
              if tag.a:
                self.article['title'] = ''.join(tag.a.findAll(text=True))
                self.article['url'] = self._path2url(tag.a['href'])

              if tag.find('div', {'class': 'gs_a'}):
                year = self.year_re.findall(tag.find('div', {'class': 'gs_a'}).text)
                self.article['year'] = year[0] if len(year) > 0 else None

              if tag.find('div', {'class': 'gs_fl'}):
                self._parse_links(tag.find('div', {'class': 'gs_fl'}))

        if self.article['title']:
            self.handle_article(self.article)


class ScholarQuerier():
    """
    ScholarQuerier instances can conduct a search on Google Scholar
    with subsequent parsing of the resulting HTML content.  The
    articles found are collected in the articles member, a list of
    Article instances.
    """
    SCHOLAR_URL = 'http://scholar.google.com/scholar?hl=en&q=%(query)s+author:%(author)s&btnG=Search&as_subj=eng&as_sdt=1,5&as_ylo=&as_vis=0'
    NOAUTH_URL = 'http://scholar.google.com/scholar?hl=en&q=%(query)s&btnG=Search&as_subj=eng&as_std=1,5&as_ylo=&as_vis=0'
    BIBTEX_URL = 'http://scholar.google.com/scholar?q=info:%(ref_id)s:scholar.google.com/&output=cite&hl=de&as_sdt=0,5'

    """
    Older URLs:
    http://scholar.google.com/scholar?q=%s&hl=en&btnG=Search&as_sdt=2001&as_sdtp=on
    """

    UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:21.0) Gecko/20100101 Firefox/21.0'
    CJ = CookieJar()

    class Parser(ScholarParser120726):
        def __init__(self, querier):
            ScholarParser.__init__(self)
            self.querier = querier

        def handle_article(self, art):
            self.querier.add_article(art)

    def __init__(self, author='', scholar_url=None, count=0):
        self.articles = []
        self.author = author

        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.CJ))
        self.opener.addheaders = [('User-Agent', self.UA)]

        # Clip to 100, as Google doesn't support more anyway
        self.count = min(count, 100)

        if author == '':
            self.scholar_url = self.NOAUTH_URL
        else:
            self.scholar_url = scholar_url or self.SCHOLAR_URL

        if self.count != 0:
            self.scholar_url += '&num=%d' % self.count

    def query(self, search, bibtex=False):
        """
        This method initiates a query with subsequent parsing of the
        response.
        """
        url = self.scholar_url % {'query': urllib.quote(search.encode('utf-8')), 'author': urllib.quote(self.author)}

        # This gets us the normal information, available from the google
        # scholar results page
        r = self.opener.open(url)
        html = r.read()
        self.parse(html)

        # After loading the result articles, get the bibtex, if requested
        if bibtex:
            for art in self.articles:
                self._bibtech_query(art)


    def _bibtech_query(self, article):
        """
        Load the Bibtex for an article. The query method has to be called first,
        as we need a cookie from google. Then we need to aquire a unique
        identifier by loading an AJAX page before we can access the bibtex.

        Returns the bibtex string
        """
        url = self.BIBTEX_URL % { 'ref_id': article['bibtex_id'] }

        # First we need to open the citation page
        r = self.opener.open(url)
        cite_html = r.read()

        # Now we extract the bibtex link with the unique identifier
        parser = ScholarParser()
        bibtex_path = parser.parse_bibtex_link(cite_html)

        url = 'http://scholar.google.com%(bibtex_path)s' % { 'bibtex_path': bibtex_path }

        # Finally we can open the bibtex text
        r = self.opener.open(url)
        bibtex_txt = r.read()

        # Strip last newline and add information to article
        article.bibtex_string = bibtex_txt.rstrip(' \n')

    def parse(self, html):
        """
        This method allows parsing of existing HTML content.
        """
        parser = self.Parser(self)
        parser.parse(html)

    def add_article(self, art):
        self.articles.append(art)


def bib(query, author, count):
    querier = ScholarQuerier(author=author, count=count)
    querier.query(query, True)
    articles = querier.articles
    if count > 0:
        articles = articles[:count]
    for art in articles:
        print art.as_bib() + '\n'

def txt(query, author, count):
    querier = ScholarQuerier(author=author, count=count)
    querier.query(query)
    articles = querier.articles
    if count > 0:
        articles = articles[:count]
    for art in articles:
        print art.as_txt() + '\n'

def csv(query, author, count, header=False, sep='|'):
    querier = ScholarQuerier(author=author, count=count)
    querier.query(query)
    articles = querier.articles
    if count > 0:
        articles = articles[:count]
    for art in articles:
        result = art.as_csv(header=header, sep=sep)
        print result.encode('utf-8')
        header = False

def url(title, author):
    querier = ScholarQuerier(author=author)
    querier.query(title)
    articles = querier.articles
    for article in articles:
        if "".join(title.lower().split()) == "".join(article['title'].lower().split()):
            return article['url'], article['year']
    return None, None

def titles(author):
    querier = ScholarQuerier(author=author)
    querier.query('')
    articles = querier.articles
    titles = []
    for article in articles:
      titles.append(article['title'])
    return titles

def main():
    usage = """scholar.py [options] <query string>
A command-line interface to Google Scholar."""

    fmt = optparse.IndentedHelpFormatter(max_help_position=50,
                                         width=100)
    parser = optparse.OptionParser(usage=usage, formatter=fmt)
    parser.add_option('-a', '--author',
                      help='Author name')
    parser.add_option('--bib', action='store_true',
                      help='Print only bibtex')
    parser.add_option('--csv', action='store_true',
                      help='Print article data in CSV format (separator is "|")')
    parser.add_option('--csv-header', action='store_true',
                      help='Like --csv, but print header line with column names')
    parser.add_option('--txt', action='store_true',
                      help='Print article data in text format')
    parser.add_option('-c', '--count', type='int',
                      help='Maximum number of results')
    parser.set_defaults(count=0, author='')
    options, args = parser.parse_args()

    if len(args) == 0:
        print 'Hrrrm. I  need a query string.'
        sys.exit(1)

    query = ' '.join(args)

    if options.bib:
        bib(query, author=options.author, count=options.count)
    elif options.csv:
        csv(query, author=options.author, count=options.count)
    elif options.csv_header:
        csv(query, author=options.author, count=options.count, header=True)
    else:
        txt(query, author=options.author, count=options.count)

if __name__ == "__main__":
    main()

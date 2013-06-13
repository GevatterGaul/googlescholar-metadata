#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3' #Based on B&N plugin by Grant Drake
__copyright__ = '2013, Benjamin Behringer <mail at benjamin-behringer.de>'
__docformat__ = 'en'

import re
import datetime
from threading import Thread
from calibre.ebooks.metadata.book.base import Metadata
from .scholar import ScholarQuerier
from .bib import Bibparser

class Worker(Thread): # Get details
    '''
    Download paper information from google scholar in separate thread.
    '''

    def __init__(self, result_queue, log, query_title, query_authors, plugin, num=1):
        Thread.__init__(self)
        self.daemon = True
        self.result_queue = result_queue
        self.log = log
        self.count = num
        self.plugin = plugin
        self.query_title, self.query_authors = query_title, query_authors

    def run(self):
        try:
            self._get_results()
        except:
            self.log.exception('_get_results failed')

    def _get_results(self):
        """ Download Information from Google Scholar """
        querier = ScholarQuerier(author=self.query_authors[0], count=self.count)
        querier.query(self.query_title, bibtex=True)
        articles = querier.articles
        if self.count > 0:
            articles = articles[:self.count]
        for num, art in enumerate(articles):
            bibtex_string = art.as_bib()

            bib = Bibparser(bibtex_string)
            bib.parse()
            slug = bib.records.keys()[0]
            bib_dict = bib.records[slug]

            title = bib_dict.get('title')

            authors = []

            for author in bib_dict.get('author', []):
                # Ignore non existant given names
                given_name = '%s ' % author.get('given') if 'given' in author else ''
                # Add full stops after abbreviated name parts
                given_name = re.sub(r'(^| +)([A-Z])( +|$)', r'\1\2.\3', given_name)

                authors.append('%s%s' % (given_name, author['family']))

            mi = Metadata(title, authors)

            mi.set_identifier('googlescholar', slug)
            mi.source_relevance = 100-num

            if 'publisher' in bib_dict:
                mi.publisher = bib_dict['publisher']

            if 'issued' in bib_dict:
                if 'literal' in bib_dict['issued']:
                    year = int(bib_dict['issued']['literal'])

                    from calibre.utils.date import utc_tz
                    # We only have the year, so let's use Jan 1st
                    mi.pubdate = datetime.datetime(year, 1, 1, tzinfo=utc_tz)

            self.plugin.clean_downloaded_metadata(mi)
            self._log_metadata(mi)
            self.result_queue.put(mi, True)
            self.log.info(self.result_queue.qsize())

    def _log_metadata(self, mi):
        self.log.info('-'*70)
        self.log.info(mi)
        self.log.info('-'*70)


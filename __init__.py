#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2013, Benjamin Behringer <mail at benjamin-behringer.de>'
__docformat__ = 'en'

from calibre.ebooks.metadata.sources.base import Source

class GoogleScholar(Source):

    name = 'Google Scholar'
    description = _('Download metadata for papers from Google Scholar')
    version = (0, 1, 0)
    author = 'Benjamin Behringer'
    minimum_calibre_version = (0, 9, 0)

    capabilities = frozenset(['identify'])
    touched_fields = frozenset ([
        'title',
        'authors',
        'publisher',
        'pubdate',
    ])

    # def get_book_url(self, identifiers):
    #     return 'googlescholar', 

    def config_widget(self):
        '''
        Overriding the default configuration screen for our own custom configuration
        '''
        from calibre_plugins.googlescholar_metadata.config import ConfigWidget
        return ConfigWidget(self)

    def identify(self, log, result_queue, abort, title=None, authors=None,
            identifiers={}, timeout=30):

        import calibre_plugins.googlescholar_metadata.config as cfg
        from calibre_plugins.googlescholar_metadata.worker import Worker

        # Search for results in different thread, as searching takes time and blocks...
        worker = Worker(result_queue, log, title, authors, self, cfg.getOption(cfg.KEY_MAX_DOWNLOADS))
        worker.start()

        while not abort.is_set():
        	worker.join(0.2)

        	if not worker.is_alive():
        		break

        log.info('Out of worker: %s' % result_queue.qsize())

        return None
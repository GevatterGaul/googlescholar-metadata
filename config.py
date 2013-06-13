#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3' #Based on B&N plugin by Grant Drake
__copyright__ = '2013, Benjamin Behringer <mail at benjamin-behringer.de>'
__docformat__ = 'en'

from PyQt4 import QtGui
from PyQt4.Qt import QLabel, QGridLayout, Qt, QGroupBox, QCheckBox
from calibre.gui2.metadata.config import ConfigWidget as DefaultConfigWidget
from calibre.utils.config import JSONConfig

STORE_NAME = 'Options'
# KEY_MAX_PAGES = 'maxPages'
KEY_MAX_DOWNLOADS = 'maxDownloads'
KEY_GET_ADDITIONAL_INFO = 'getAdditionalInfo'
KEY_THRESHOLD = 'threshold'
KEY_TRY_EXCHANGING = 'tryExchanging'

DEFAULT_STORE_VALUES = {
    KEY_MAX_DOWNLOADS: 1,
}

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/GoogleScholar')

# Set defaults
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES

def getOption(option_key):
    default_value = DEFAULT_STORE_VALUES[option_key]
    return plugin_prefs[STORE_NAME].get(option_key, default_value)

class ConfigWidget(DefaultConfigWidget):

    def __init__(self, plugin):
        DefaultConfigWidget.__init__(self, plugin)
        c = plugin_prefs[STORE_NAME]

        other_group_box = QGroupBox('Other options', self)
        self.l.addWidget(other_group_box, self.l.rowCount(), 0, 1, 2)
        other_group_box_layout = QGridLayout()
        other_group_box.setLayout(other_group_box_layout)

        max_downloads_label = QLabel('Maximum title/author search matches to download/evaluate (1 = fastest):', self)
        max_downloads_label.setToolTip('More matches means higher chance of better\n'
                             'metadata (but not necessarily).\n')
        other_group_box_layout.addWidget(max_downloads_label, 1, 0, 1, 1)
        self.max_downloads_spin = QtGui.QSpinBox(self)
        self.max_downloads_spin.setMinimum(1)
        self.max_downloads_spin.setMaximum(100)
        self.max_downloads_spin.setProperty('value', c.get(KEY_MAX_DOWNLOADS, DEFAULT_STORE_VALUES[KEY_MAX_DOWNLOADS]))
        other_group_box_layout.addWidget(self.max_downloads_spin, 1, 1, 1, 1)
        other_group_box_layout.setColumnStretch(2, 1)

    def commit(self):
        DefaultConfigWidget.commit(self)
        new_prefs = {}
        new_prefs[KEY_MAX_DOWNLOADS] = int(unicode(self.max_downloads_spin.value()))
        plugin_prefs[STORE_NAME] = new_prefs


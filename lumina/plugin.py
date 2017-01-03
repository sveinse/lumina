# -*- python -*-
from __future__ import absolute_import


class Plugin(object):
    name = 'PLUGIN'

    CONFIG = {}

    def configure(self):
        pass
    def setup(self, main):
        pass
    def close(self):
        pass

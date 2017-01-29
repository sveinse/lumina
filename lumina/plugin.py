# -*- python -*-
from __future__ import absolute_import


class Plugin(object):
    name = 'PLUGIN'

    CONFIG = {}

    def override_name(self, name, main):
        ''' Override the configured name when instanciating this class.
            This method shall only be used in very special cases, such as
            by the admin plugin.
        '''
        return name

    def configure(self):
        ''' Configure self.commands and self.events '''

    def setup(self, main):
        ''' Setup the class and services. '''

    def close(self):
        ''' Close any open files and connections '''

# -*- python -*-
from __future__ import absolute_import

from lumina.log import Logger
from lumina.state import ColorState


class Plugin(object):

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

        self.log = Logger(namespace=self.name)
        self.status = ColorState(log=self.log)

    def close(self):
        ''' Close any open files and connections '''

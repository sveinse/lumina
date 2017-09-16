# -*- python -*-
from __future__ import absolute_import

from lumina.log import Logger
from lumina.state import ColorState


class Plugin(object):

    # Plugin configurations, both local and global
    CONFIG = {}
    GLOBAL_CONFIG = {}

    def __init__(self, main):
        pass

    def override_name(self, name, main):
        ''' Override the configured name when instanciating this class.
            This method shall only be used in very special cases, such as
            by the admin plugin.
        '''
        return name

    def configure(self, main):
        ''' Configure the plugin. This method will be called before setup()
            and expects to setup any internal attributes.
        '''

    def setup(self, main):
        ''' Setup and start the services this plugin provides.
        '''

        self.log = Logger(namespace=self.name)
        self.status = ColorState(log=self.log, name=self.name)

    def close(self):
        ''' Close any open files and connections
        '''

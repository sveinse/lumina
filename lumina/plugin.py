# -*- python -*-
from __future__ import absolute_import

#from lumina.log import Logger
#from lumina.state import ColorState


class Plugin(object):

    # Plugin configurations, both local and global
    CONFIG = {}
    GLOBAL_CONFIG = {}

    # List of plugin dependencies
    DEPENDS = []

    def __init__(self, master):
        pass

    def configure(self, master):
        ''' Configure the plugin. This method will be called before setup()
            and expects to setup any internal attributes.
        '''

    def setup(self, master):
        ''' Setup and start the services this plugin provides.
        '''

    def close(self):
        ''' Close any open files and connections
        '''

# -*- python -*-
""" Base class for plugins """
from __future__ import absolute_import, division, print_function


class Plugin(object):
    """ Base object class for plugins """

    # Plugin configurations, both local and global
    CONFIG = {}
    GLOBAL_CONFIG = {}

    # List of plugin dependencies
    DEPENDS = ()

    # List of function names to run when configuring the class
    CONFIGURE_METHODS = ('configure', 'setup')


    def configure(self):
        ''' Configure the plugin. This method will be called before setup()
            and expects to setup any internal attributes.
        '''

    def setup(self):
        ''' Setup and start the services this plugin provides.
        '''

    def close(self):
        ''' Close any open files and connections
        '''

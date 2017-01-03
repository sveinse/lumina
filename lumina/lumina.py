# -*- python -*-
from __future__ import absolute_import

import re
from importlib import import_module
from twisted.internet import reactor

from .config import Config
from .log import *



class Lumina(object):

    # Overall (default) config options
    CONFIG = {
        'conffile'   : dict( default='lumina.conf', help='Configuration file' ),
        'plugins'    : dict( default=( ), help='Plugins to load', type=tuple ),
    }


    def setup(self, conffile=None):

        #== CONFIGUATION
        self.config = config = Config(settings=self.CONFIG)

        # Load new configuration
        if conffile:
            self.config.readconfig(conffile)
            self.config.set('conffile', conffile)

        #== PLUGINS
        self.plugins = plugins = { }
        re_name = re.compile(r'^([\w]+)(\(([\w]+)\))?$')

        # Iterate over the plugins from config
        for module in config['plugins']:

            # Ignore empty plugin names
            module = module.strip()
            if not len(module):
                continue

            # Check the name syntax
            m = re_name.match(module)
            if not m:
                err("Syntax error in plugin name: '%s'" %(module))
                continue

            # Check if the syntax "plugin(name)" has been used
            name = module
            if m.group(3) is not None:
                module = m.group(1)
                name = m.group(3)

            # Require unique names
            if name in plugins:
                err("Plugin '%s' already exist" %(name))
                continue

            try:
                log("Loading plugin %s..." %(module))

                plugin = import_module('lumina.plugins.' + module).PLUGIN()
                plugin.name = name
                plugin.module = module

                log("===  Registering plugin %s as %s" %(module,name))
                self.plugins[name] = plugin

                # FIXME: Add global config options coming from the plugins. Either via
                #        global=True, or as a separate GLOBAL_CONFIG variable

                # Setup plugin
                plugin.configure()
                config.register(plugin.CONFIG,name=name)
                plugin.setup(main=self)

                # Setup for closing the plugin on close
                reactor.addSystemEventTrigger('before','shutdown',plugin.close)

            except Exception as e:
                import traceback
                err("Failed to load plugin %s, ignoring. Exception:\n" %(module,) + traceback.format_exc())

        #== Register own shutdown
        reactor.addSystemEventTrigger('before','shutdown',self.close)

        # Missing plugins?
        if len(plugins) == 0:
            warn("No plugins have been configured. Doing nothing.")


    def close(self):
        pass


    #== SERVICE FUNCTIONS
    def get_plugin_by_module(self, module):
        ''' Return the instance for plugin given by the module argument '''
        for name,inst in self.plugins.items():
            if inst.module == module:
                return inst
        return None

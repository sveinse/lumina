# -*- python -*-
from __future__ import absolute_import

import re
from importlib import import_module
from twisted.internet import reactor

from lumina.config import Config
from lumina.log import Logger
from lumina.state import ColorState


class FailedPlugin(object):
    ''''''



class Lumina(object):

    # Overall (default) config options
    CONFIG = {
        'conffile'   : dict( default='lumina.conf', help='Configuration file' ),
        'plugins'    : dict( default=( ), help='Plugins to load', type=tuple ),
    }


    def setup(self, conffile=None):
        self.log = Logger(namespace='-')

        #== CONFIGUATION
        self.config = config = Config(settings=self.CONFIG)

        # Load new configuration
        if conffile:
            self.config.readconfig(conffile)
            self.config.set('conffile', conffile)

        #== PLUGINS
        self.plugins = { }
        self.sequence = []
        re_name = re.compile(r'^([\w]+)(\(([\w]+)\))?$')

        count = 0

        # Iterate over the plugins from config
        for module in config['plugins']:

            # Ignore empty plugin names
            module = module.strip()
            if not len(module):
                continue

            count += 1
            name = module

            try:

                # Check the name syntax
                m = re_name.match(module)
                if not m:
                    raise Exception("Syntax error in plugin name")

                # Check if the syntax "plugin(name)" has been used
                if m.group(3) is not None:
                    module = m.group(1)
                    name = m.group(3)

                # Require unique names
                if name in self.plugins:
                    raise Exception("Plugin already exist" %(name))

                self.log.info("Loading plugin {m}...", m=module)

                plugin = import_module('lumina.plugins.' + module).PLUGIN()
                plugin.name = name
                plugin.module = module
                plugin.module_sequence = count

                self.log.info("===  Registering #{c} plugin {m} as {n}", c=count, m=module, n=name)
                self.plugins[name] = plugin
                self.sequence.append(name)

                # FIXME: Add global config options coming from the plugins. Either via
                #        global=True, or as a separate GLOBAL_CONFIG variable

                # Setup plugin
                plugin.configure()
                config.register(plugin.CONFIG,name=name)
                plugin.setup(main=self)

                # Setup for closing the plugin on close
                reactor.addSystemEventTrigger('before','shutdown',plugin.close)


            # -- Handle errors loading
            except Exception as e:
                msg = "Failed to load plugin '{m}': {e}".format(m=module,e=e)
                self.log.failure("{m}  --  IGNORING", m=msg)

                # Put in a empty failed placeholder
                plugin = FailedPlugin()
                plugin.name = name
                plugin.module = name
                plugin.module_sequence = count
                plugin.status = ColorState('RED',log=self.log,why=msg)

                self.plugins[name] = plugin
                if name not in self.sequence:
                    self.sequence.append(name)


        #== Register own shutdown
        reactor.addSystemEventTrigger('before','shutdown',self.close)

        # Missing plugins?
        if not self.plugins:
            self.log.warn("No plugins have been configured. Doing nothing.")


    def close(self):
        pass


    #== SERVICE FUNCTIONS
    def get_plugin_by_module(self, module):
        ''' Return the instance for plugin given by the module argument '''
        for name,inst in self.plugins.items():
            if inst.module == module:
                return inst
        return None

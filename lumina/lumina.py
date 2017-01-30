# -*- python -*-
from __future__ import absolute_import

import re
import os
import socket
from binascii import hexlify
from importlib import import_module
from twisted.internet import reactor

from lumina.config import Config
from lumina.log import Logger
from lumina.state import ColorState
from lumina.plugin import Plugin



class FailedPlugin(Plugin):
    ''' Plugin failed to load. '''
    name = "FAILED"



class Lumina(object):

    # The plugin= syntax in the configuration file
    RE_PLUGIN_SYNTAX = re.compile(r'^([\w]+)(\(([\w]+)\))?$')

    # Overall (default) config options
    CONFIG = {
        'conffile'   : dict(default='lumina.conf', help='Configuration file'),
        'plugins'    : dict(default=(), help='Plugins to load', type=tuple),
    }


    def setup(self, conffile=None):
        self.log = Logger(namespace='-')
        self.status = ColorState(log=self.log)

        #== GENERAL INFORMATION
        self.hostname = socket.gethostname()
        self.hostid = hexlify(os.urandom(4))
        self.pid = os.getpid()

        self.log.info("Host {host} [{hostid}], PID {pid}",
                      host=self.hostname, hostid=self.hostid, pid=self.pid)


        #== CONFIGUATION
        self.config = config = Config(settings=self.CONFIG)

        # Load new configuration
        if conffile:
            self.config.readconfig(conffile)
            self.config.set('conffile', conffile)

        #== PLUGINS
        self.plugins = []

        count = 0

        # Ensure the admin plugin is always loaded
        plugins = list(config['plugins'])
        if 'admin' not in plugins:
            plugins.insert(0, 'admin')

        # Iterate over the plugins from config
        for module in plugins:

            # Ignore empty plugin names
            module = module.strip()
            if not len(module):
                continue

            count += 1
            name = module

            try:

                # Check the name syntax
                m = self.RE_PLUGIN_SYNTAX.match(module)
                if not m:
                    raise Exception("Syntax error in plugin name")

                # Check if the syntax "plugin(name)" has been used
                if m.group(3) is not None:
                    module = m.group(1)
                    name = m.group(3)

                self.log.info("Loading plugin {m}...", m=module)

                plugin = import_module('lumina.plugins.' + module).PLUGIN()

                # Get the name to use from the plugin if it is overridden
                confname = name
                name = plugin.override_name(confname, self)
                if name != confname:
                    self.log.warn("Plugin name overridden from {o} to {n}", o=confname, n=name)

                # Require unique names
                if self.get_plugin_by_name(name):
                    raise Exception("Plugin already exist" %(name))

                # Store plugin related information
                plugin.name = name
                plugin.module = module
                plugin.sequence = count

                self.log.info("===  Registering #{c} plugin {m} as {n}", c=count, m=module, n=name)
                self.plugins.append(plugin)

                # FIXME: Add global config options coming from the plugins. Either via
                #        global=True, or as a separate GLOBAL_CONFIG variable

                # Setup plugin
                plugin.configure()
                config.register(plugin.CONFIG, name=name)
                plugin.setup(main=self)

                # Setup for closing the plugin on close
                reactor.addSystemEventTrigger('before', 'shutdown', plugin.close)


            # -- Handle errors loading
            except Exception as e:    # pylint: disable=broad-except
                msg = "Failed to load plugin '{m}': {e}".format(m=module, e=e)
                self.log.failure("{m}  --  IGNORING", m=msg)

                # Put in a empty failed placeholder
                plugin = FailedPlugin()
                plugin.name = name
                plugin.module = FailedPlugin.name
                plugin.sequence = count
                plugin.status = ColorState('RED', log=self.log, why=msg)

                # FIXME: self.plugins might already have added the failed plugin
                self.plugins.append(plugin)


        #== Register own shutdown
        reactor.addSystemEventTrigger('before', 'shutdown', self.close)

        # Missing plugins?
        if not self.plugins:
            self.log.warn("No plugins have been configured. Doing nothing.")


    def close(self):
        pass


    #== SERVICE FUNCTIONS
    def get_plugin_by_module(self, module):
        ''' Return the instance for plugin given by the module argument '''
        for inst in self.plugins:
            if inst.module == module:
                return inst

    def get_plugin_by_name(self, name):
        ''' Return the instance for a plugin given by the name '''
        for inst in self.plugins:
            if inst.name == name:
                return inst

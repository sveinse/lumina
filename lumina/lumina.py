# -*- python -*-
from __future__ import absolute_import

import re
import os
import socket
from binascii import hexlify
from importlib import import_module
from datetime import datetime

from twisted.internet import reactor

from lumina.config import Config
from lumina.log import Logger
from lumina.state import ColorState
from lumina.plugin import Plugin
from lumina.utils import topolgical_sort



class FailedPlugin(Plugin):
    ''' Plugin failed to load. '''
    name = "FAILED"



class Lumina(object):

    # The plugin= syntax in the configuration file
    RE_PLUGIN_SYNTAX = re.compile(r'^([\w.]+)(\(([\w.]+)\))?$')

    # Overall (default) global config options
    GLOBAL_CONFIG = {
        'conffile'   : dict(default='lumina.json', help='Configuration file'),
        'plugins'    : dict(default=[], help='Plugins to load', type=list),
        'hostid'     : dict(default=socket.gethostname(), help='Unique id for this host'),
    }


    # Setup Lumina. This is run before the reactpr has been started
    def __init__(self, conffile=None):
        self.log = Logger(namespace='-')
        self.status = ColorState(log=self.log)

        #== CONFIGUATION
        self.config = config = Config()
        config.add_templates(self.GLOBAL_CONFIG)

        # Load new configuration
        if conffile:
            self.config.readconfig(conffile)
            self.config['conffile'] = conffile

        #== GENERAL INFORMATION
        self.hostname = socket.gethostname()
        # Use hostname as host ID rather than making a random ID. Random ID
        # does is not static across reboots
        self.hostid = hexlify(os.urandom(3))
        #self.hostid = config['hostid']
        self.pid = os.getpid()
        self.starttime = datetime.utcnow()

        self.log.info("Host {host} [{hostid}], PID {pid}",
                      host=self.hostname, hostid=self.hostid, pid=self.pid)


    def setup(self):

        self.log.info("Starting plugins...")

        #== PLUGINS
        self.plugins = {}
        self.plugin_count = 0
        self.plugin_deps = {}

        plugins = list(self.config['plugins'])
        for i, module in enumerate(plugins):

            # Ignore empty plugin names
            module = module.strip()
            if not len(module):
                continue

            # Check the name syntax
            m = self.RE_PLUGIN_SYNTAX.match(module)
            if not m:
                self.log.error("Syntax error in plugin name '%s' (index %s)  --  IGNORING" %(
                    module, i+1))
                continue
            name = module
            if m.group(3) is not None:
                module = m.group(3)
                name = m.group(1)

            # Require unique names
            if name in self.plugins:
                self.log.error("Plugin with name '%s' already exists  -- IGNORING" %(name))
                continue

            # Load the plugin
            self.load_plugin(module, name)


        #== Load any additional dependencies
        while True:

            loaded = set()
            depends = set()
            for name, deps in self.plugin_deps.items():
                loaded.add(name)
                depends.update(deps)

            toload = depends.difference(loaded)
            if not toload:
                break

            self.log.warn("Loading missing dependencies: {l}", l=', '.join(list(toload)))
            for module in toload:

                # Load the dependency
                self.load_plugin(module)


        #== Sort the sequence
        try:
            sequence = topolgical_sort(self.plugin_deps)
            self.log.info("Setup sequence: {l}", l=", ".join(sequence))
        except:
            self.log.critical("Cyclic dependencies detected. Stopping.")
            self.log.critical("Dependencies: {d}", d=self.plugin_deps)
            raise SystemExit(1)


        #== Configure the plugins
        for name in sequence:
            try:
                self.configure_plugin(name)
            except:
                raise


        #== Register own shutdown
        reactor.addSystemEventTrigger('before', 'shutdown', self.close)

        # No plugins?
        if not self.plugins:
            self.status.set_OFF('No plugins')
            self.log.warn("No plugins have been configured. Doing nothing.")


    def close(self):
        pass


    #==
    def load_plugin(self, module, name=None):

        if name is None:
            name = module

        self.plugin_count += 1

        try:
            self.log.info("Loading plugin {m}...", m=module)

            # LOAD the plugin
            plugin = import_module('lumina.plugins.' + module).PLUGIN(self)
            plugin.failed = None

            # Registering plugin
            #self.log.info("===  Registering #{c} plugin {m} as {n}",
            #              c=self.plugin_count, m=module, n=name)

        except Exception as e:    # pylint: disable=broad-except
            msg = "Failed to load plugin '{m}': {t}: {e}".format(
                m=module, t=type(e).__name__, e=e.message)
            self.log.failure("{m}", m=msg)

            # Put in a empty failed placeholder
            plugin = FailedPlugin(self)
            module = FailedPlugin.name
            plugin.failed = "%s: %s" %(type(e).__name__, e.message)

            #plugin.status = ColorState('RED', log=self.log, why=msg, name=module)

        # Set common admin attributes
        plugin.name = name
        plugin.module = module
        plugin.sequence = self.plugin_count
        # plugin.failed   <-- See above

        plugin.log = Logger(namespace=plugin.name)
        plugin.status = ColorState(log=plugin.log, name=plugin.name)

        # Update master status
        plugin.status.add_callback(self.update_status, run_now=True)

        # Register plugin
        self.plugins[name] = plugin

        # Copy the plugin dependencies
        deps = [unicode(d) for d in plugin.DEPENDS]
        self.plugin_deps[name] = deps
        if deps:
            self.log.info("   depends on {d}", d=', '.join(deps))

        return plugin


    def configure_plugin(self, name):

        plugin = self.plugins[name]

        dep_status = [self.plugins[dep].failed for dep in self.plugin_deps[name]]
        if any(dep_status):
            #deps = ', '.join(self.plugin_deps[name])
            plugin.failed = "DependencyError: One of the depending plugins has failed to load"

        # Setup plugin
        if not plugin.failed:
            try:

                self.log.info("===  Setting up plugin {n}", n=name)
                self.config.add_templates(plugin.GLOBAL_CONFIG)
                self.config.add_templates(plugin.CONFIG, name=name)
                plugin.configure(master=self)
                plugin.setup(master=self)

            except Exception as e:  # pylint: disable=broad-except
                msg = "Failed to configure plugin '{n}': {t}: {e}".format(
                    n=name, t=type(e).__name__, e=e.message)
                self.log.failure("{m}", m=msg)
                plugin.failed = "%s: %s" %(type(e).__name__, e.message)

                # FIXME: What happens when the module failed?
                plugin.close()

        if plugin.failed:
            self.log.error("###  Failed plugin {n} ({e})", n=name, e=plugin.failed)
            plugin.status.set_RED(plugin.failed)

         # Setup for closing the plugin on close
        reactor.addSystemEventTrigger('before', 'shutdown', plugin.close)


    #== INTERNAL FUNCTIONS
    def update_status(self, status):  # pylint: disable=unused-variable
        (state, why) = ColorState.combine(*[plugin.status for plugin in self.plugins.itervalues()])
        self.status.set(state, why)


    #== SERVICE FUNCTIONS
    def get_plugin_by_module(self, module):
        ''' Return the instance for plugin given by the module argument '''
        for inst in self.plugins.itervalues():
            if inst.module == module:
                return inst

    def get_plugin_by_name(self, name):
        ''' Return the instance for a plugin given by the name '''
        for inst in self.plugins.itervalues():
            if inst.name == name:
                return inst

    def get_info(self):
        ''' Return a dict of info about this server '''
        return {
            'hostname'   : self.hostname,
            'hostid'     : self.hostid,
            'plugins'    : [
                {
                    'name'      : plugin.name,
                    'module'    : plugin.module,
                    'sequence'  : plugin.sequence,
                    'depends'   : plugin.DEPENDS,
                    'doc'       : plugin.__doc__,
                    'status'    : str(plugin.status),
                    'status_why': plugin.status.why,
                } for plugin in self.plugins.itervalues()],
            'status'     : str(self.status),
            'status_why' : self.status.why,
            'config'     : [
                {
                    'key'     : k,
                    'value'   : v.get('v'),
                    'default' : v.get('default'),
                    'type'    : v.get('type', str).__name__,
                    'help'    : v.get('help'),
                } for k, v in self.config.items()],
            'starttime' : self.starttime.isoformat()+'Z',
        }

# -*- python -*-
""" Master engine of lumina """
from __future__ import absolute_import

import re
import os
import socket
from binascii import hexlify
from importlib import import_module
from datetime import datetime

import lumina
from lumina.log import Logger
from lumina.state import ColorState
from lumina.plugin import Plugin
from lumina.utils import topolgical_sort
from lumina.message import Message



class Lumina(object):
    ''' Main Lumina master engine '''

    # The plugin= syntax in the configuration file
    RE_PLUGIN_SYNTAX = re.compile(r'^([\w.]+)(\(([\w.]+)\))?$')

    # Overall (default) global config options
    GLOBAL_CONFIG = {
        'conffile'   : dict(default='lumina.json', help='Configuration file'),
        'plugins'    : dict(default=[], help='Plugins to load', type=list),
        'hostid'     : dict(default=socket.gethostname(), help='Unique id for this host'),
    }

    # Default return value
    return_value = 0


    # Setup Lumina. This is run before the reactpr has been started
    def __init__(self, reactor, config=None):

        # Store reactor
        self.reactor = reactor

        self.log = Logger(namespace='-')
        self.status = ColorState(log=self.log)

        # Configuration
        self.config = config
        config.add_templates(self.GLOBAL_CONFIG)

        # General info
        self.hostname = socket.gethostname()
        # Use hostname as host ID rather than making a random ID. Random ID
        # does is not static across reboots
        self.hostid = hexlify(os.urandom(3))
        #self.hostid = config['hostid']
        self.pid = os.getpid()
        self.starttime = datetime.utcnow()

        self.log.info("Host {host} [{hostid}], PID {pid}",
                      host=self.hostname, hostid=self.hostid, pid=self.pid)


    def run(self):
        ''' Run the engine by loading plugins '''

        self.log.info("Starting plugins...")

        # Handle plugins
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

        # Load any additional plugin dependencies
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

        # Sort the sequence of plugins
        try:
            sequence = topolgical_sort(self.plugin_deps)
            self.log.info("Setup sequence: {l}", l=", ".join(sequence))
        except:
            self.log.critical("Cyclic dependencies detected. Stopping.")
            self.log.critical("Dependencies: {d}", d=self.plugin_deps)
            raise SystemExit(1)

        # Configure the plugins in the sorted order
        for name in sequence:
            try:
                self.configure_plugin(name)
            except:
                raise

        # No plugins?
        if not self.plugins:
            self.status.set_OFF('No plugins')
            self.log.warn("No plugins have been configured. Doing nothing.")


    def load_plugin(self, module, name=None):
        ''' Load the given module. Handle any failures that might occur. '''

        if name is None:
            name = module

        self.plugin_count += 1

        # Import the plugin
        try:
            self.log.info("Loading plugin {m}...", m=module)
            plugin = import_module('lumina.plugins.' + module).PLUGIN()
            plugin.failed = None

            # Registering plugin
            #self.log.info("===  Registering #{c} plugin {m} as {n}",
            #              c=self.plugin_count, m=module, n=name)

        except Exception as e:    # pylint: disable=broad-except
            msg = "Failed to load plugin '{m}': {t}: {e}".format(
                m=module, t=type(e).__name__, e=e.message)
            self.log.failure("{m}", m=msg)

            # Put in a empty failed placeholder
            module = 'FAILED'
            plugin = Plugin()
            plugin.failed = "%s: %s" %(type(e).__name__, e.message)

            #plugin.status = ColorState('RED', log=self.log, why=msg, name=module)

        # Set common admin attributes
        plugin.name = name
        plugin.module = module
        plugin.sequence = self.plugin_count
        # plugin.failed   <-- See above

        plugin.log = Logger(namespace=plugin.name)
        plugin.status = ColorState(log=plugin.log, name=plugin.name)

        # Give reference to us (FIXME, shouldn't inject references like this)
        plugin.master = self

        # Update status
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
        ''' Configure the loaded plugin '''

        plugin = self.plugins[name]

        dep_status = [self.plugins[dep].failed for dep in self.plugin_deps[name]]
        if any(dep_status):
            plugin.failed = "DependencyError: One of the depending plugins has failed to load"

        # Setup plugin
        if not plugin.failed:
            try:

                self.log.info("===  Setting up plugin {n}", n=name)
                self.config.add_templates(plugin.GLOBAL_CONFIG)
                self.config.add_templates(plugin.CONFIG, name=name)

                # Call the specified configuration methods
                for method in plugin.CONFIGURE_METHODS:
                    getattr(plugin, method)()

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
        self.reactor.addSystemEventTrigger('before', 'shutdown', plugin.close)


    #== INTERNAL FUNCTIONS
    def update_status(self, status):  # pylint: disable=W0613
        ''' Callback updating the status from all plugins '''
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



class LuminaClient(Lumina):
    ''' Client Lumina master client engine '''

    # Overall (default) global config options
    GLOBAL_CONFIG = {
        'conffile'   : dict(default='lumina.json', help='Configuration file'),
        'port'  : dict(default=5326, help='Lumina port to connect to', type=int),
        'server': dict(default='localhost', help='Lumina server to connect to'),
    }


    def run(self, command):
        Lumina.run(self)

        client = self.get_plugin_by_module('client')

        def client_ok(result):
            # FIXME
            print 'OK'
            client.protocol.transport.loseConnection()
        def client_err(failure):
            self.return_value = 1
            client.log.critical('{f}',f=failure.getErrorMessage())
        
        d = client.send(Message.create('command', '_info'))
        d.addCallback(client_ok)
        d.addErrback(client_err)
        d.addBoth(lambda a: self.reactor.stop())

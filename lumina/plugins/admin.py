# -*- python -*-
from __future__ import absolute_import

from lumina.node import Node


class Admin(Node):
    ''' Administration web interface node '''

    def override_name(self, name, main):
        ''' Name this node according to the hostid from the main class '''
        return main.hostid

    def configure(self, main):
        self.commands = {
            'config' : lambda a: self.config(),
            'info'   : lambda a: self.info(),
            'nodes'  : lambda a: self.nodes(),
            'plugins': lambda a: self.plugins(),
            'server' : lambda a: self.server(),
        }

    def setup(self, main):
        Node.setup(self, main)

        self.main = main
        self.status.set_GREEN()


    def close(self):
        # Help the GC to clean up
        self.main = None


    # -- COMMANDS --
    def info(self):
        ''' Return info about the lumina engine '''
        main = self.main
        return {
            'hostname'   : main.hostname,
            'hostid'     : main.hostid,
            'plugins'    : [plugin.name for plugin in main.plugins],
            'n_config'   : len(main.config),
            'status'     : str(main.status),
            'status_why' : main.status.why,
        }

    def server(self):
        ''' Return info about the server (if enabled) '''
        main = self.main
        server = main.get_plugin_by_module('server')
        if not server:
            return {}
        hosts = [node.hostid for node in server.nodes]
        return {
            'nodes'      : [node.name for node in server.nodes],
            'hosts'      : tuple(set(hosts)),
            'n_commands' : len(server.commands),
            'n_events'   : len(server.events),
            'status'     : str(server.status),
            'status_why' : str(server.status.why),
        }

    def plugins(self):
        ''' Return an array with the list of plugins running '''
        main = self.main
        response = []
        for plugin in main.plugins:
            response.append({
                'name'      : plugin.name,
                'module'    : plugin.module,
                'sequence'  : plugin.sequence,
                'doc'       : plugin.__doc__,
                'status'    : str(plugin.status),
                'status_why': plugin.status.why,
            })
        return response

    def config(self):
        ''' Return an array with the config options '''
        main = self.main
        keys = main.config.keys()
        keys.sort()
        response = []
        for k in keys:
            c = main.config.getdict(k)
            response.append({
                'key'     : k,
                'value'   : c.get('v'),
                'default' : c.get('default'),
                'type'    : c.get('type', str).__name__,
                'help'    : c.get('help'),
            })
        return response

    def nodes(self):
        ''' Return an array of all connected nodes (if server is enabled) '''
        main = self.main
        server = main.get_plugin_by_module('server')
        if not server:
            return []
        response = []
        for node in server.nodes:
            response.append({
                'name'        : node.name,
                'nodeid'      : node.nodeid,
                'hostname'    : node.hostname,
                'hostid'      : node.hostid,
                'module'      : node.module,
                'seqence'     : node.sequence,
                'status'      : node.status,
                'status_why'  : node.status_why,
                'n_commands'  : len(node.commands),
                'n_events'    : len(node.events),
                'lastactivity' : node.lastactivity.isoformat()+'Z',
            })
        return response



# Main plugin object class
PLUGIN = Admin

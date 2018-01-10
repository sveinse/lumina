# -*- python -*-
""" Lumina node server plugin """
from __future__ import absolute_import, division, print_function

from datetime import datetime

from twisted.internet.protocol import Factory
from twisted.internet.task import LoopingCall

from lumina.plugin import Plugin
from lumina.exceptions import (NodeConfigException, UnknownCommandException,
                               UnknownMessageException, NodeRegistrationException)
from lumina.log import Logger
from lumina.protocol import LuminaProtocol
from lumina.state import ColorState
from lumina.compat import compat_itervalues


# FIXME: Add this as a config statement

# Timeout before a node is considered dead and will be disconnected. Should be
# a longer interval than the nodes keepalive interval.
NODE_TIMEOUT = 180



class ServerProtocol(LuminaProtocol):
    ''' Server communication protocol '''
    keepalive_interval = NODE_TIMEOUT


    def __init__(self, parent, **kw):
        LuminaProtocol.__init__(self, parent, **kw)
        self.servername = parent.name

        # Must have new logger as we change the namespace for it when
        # clients register a node name (the default is to use parent.log)
        self.log = Logger(namespace=self.servername)

        # Remote node data
        self.nodeid = None
        self.hostname = None
        self.hostid = None
        self.module = None
        self.events = []
        self.commands = []

        # Remote node status
        self.status = ColorState(log=self.log)
        self.status.add_callback(self.parent.update_status, run_now=True)

        self.link.add_callback(self.parent.update_status, run_now=True)


    def connectionMade(self):
        LuminaProtocol.connectionMade(self)

        self.log.namespace = self.servername + ':' + self.peer
        self.log.info("Connect from {ip}", ip=self.peer, system=self.servername)

        # Set default before registration
        self.hostname = self.peer

        # Register with parent class
        self.parent.connectionMade(self)


    def connectionLost(self, reason):
        self.log.info("Lost connection from '{n}' ({ip})", n=self.name, ip=self.peer)
        LuminaProtocol.connectionLost(self, reason)

        # Set remote note status to off when we lose connection
        self.status.set_OFF()

        # Unregister parent class
        self.parent.connectionLost(self, reason)


    def keepalivePing(self):
        ''' Repurpose the keepalive to break the connection if it times out.
         '''
        self.log.info("Communication timeout from '{n}' ({ip})", n=self.name, ip=self.peer)
        self.transport.loseConnection()


    def messageReceived(self, message):
        ''' Handle messages from nodes '''
        return self.parent.messageReceived(self, message)




class ServerFactory(Factory):
    ''' Factory generator for node connections/protocols '''
    noisy = False

    def __init__(self, parent):
        self.parent = parent
        self.name = parent.name
        self.sequence = 1

    def buildProtocol(self, addr):
        protocol = ServerProtocol(parent=self.parent, sequence=self.sequence)
        self.sequence += 1
        return protocol

    def doStart(self):
        self.parent.status.set_YELLOW('Waiting for connections')
        Factory.doStart(self)

    def doStop(self):
        self.parent.status.set_OFF()
        Factory.doStop(self)



class Server(Plugin):
    ''' Lumina node server.
    '''

    GLOBAL_CONFIG = {
        'port': dict(default=5326, help='Lumina server port', type=int),
    }
    CONFIG = {
        'nodes': dict(default=[], help='List of nodes', type=list),
    }


    def configure(self):

        self.server_commands = {
            '_info': lambda a: self.master.get_info(),
            '_name': lambda a: self.master.hostname,
            '_server': lambda a: self.get_info(),
        }


    def setup(self):

        # -- Config options
        self.port = self.master.config.get('port')
        self.nodelist = self.master.config.get('nodes', name=self.name)

        # -- List of server commands and events
        self.events = []
        self.commands = {}
        self.add_commands(self.server_commands)

        # -- List of connections
        self.connections = []
        self.node_sequence = 0

        self.node_status = ColorState(log=self.log, state='OFF')

        # -- Create list of expected unconnected nodes
        #    Do not use dict comprehension here, as the dict must be updated
        #    one by one. The ServerProtocol() instance creation will call
        #    self.update_status() which in turn uses self.nodes
        self.nodes = {}
        for n in self.nodelist:
            self.nodes[n] = ServerProtocol(self)
        for n in self.nodes:
            self.nodes[n].name = n

        # -- Setup default do-nothing handler for the incoming events
        self.handle_event = lambda a: self.log.info("Ignoring event '{a}'", a=a)

        # -- Start the server
        self.factory = ServerFactory(parent=self)
        self.master.reactor.listenTCP(self.port, self.factory)


    def close(self):
        for node in self.connections:
            if node.connected:
                node.transport.loseConnection()


    def connectionMade(self, node):
        ''' Add the connected node client '''
        self.connections.append(node)
        self.status.set_GREEN()


    def connectionLost(self, node, reason):
        ''' Remove the disconnected node client '''
        self.connections.remove(node)
        if not self.connections:
            self.status.set_YELLOW('No nodes connected')

        if node.events:
            self.remove_events(node.events)
            node.events = []

        if node.commands:
            self.remove_commands(node.commands)
            node.commands = []


    def messageReceived(self, node, message):
        ''' Handle message from nodes '''

        cmd = message.name

        # -- Command type
        if message.is_type('command'):

            # -- Register node name
            if cmd == 'register':

                # Register with the server
                result = self.register_node(node, message.args[0])
                if result:
                    node.log.error('Node registration failed: {e}', e=result)
                    return result

                # Set logging name
                node.log.namespace = node.servername + ':' + node.name

                # Respond to the node if the node registration was successful
                return None

            # -- Handle status update
            elif cmd == 'status':

                # Not really interested in the old state in message.args[1]?
                node.status.set(message.args[0], why=message.args[2])
                return None

            # -- General commands
            #
            # Note that this command will be called on non-existing commmands
            # which is intended behaviour.
            return self.run_command(message)


        # -- Event type
        elif message.is_type('event'):

            prefix = node.name + '/'

            # -- Check that the event is valid and registred
            if not cmd.startswith(prefix):
                node.log.error("Ignoring undeclared event '{m}'", m=message)
                return None

            cmd = cmd.replace(prefix, '')
            if cmd not in self.events:
                node.log.error("Ignoring undeclared event '{m}'", m=message)
                return None

            # -- A new incoming event.
            return self.handle_event(message)


        # -- Unknown message type
        else:
            node.log.error("Unexpectedly received message {m}", m=message)
            raise UnknownMessageException("Unknown message type: '%s'" %(message.type,))


    def register_node(self, node, params):
        ''' Check and register a node. '''

        # -- Transfer parameters to node
        node.name = name = params.get('node')
        node.nodeid = params.get('nodeid')
        node.hostname = params.get('hostname')
        node.hostid = params.get('hostid')
        node.module = params.get('module')

        # -- Set logging names
        node.status.name = node.name
        node.link.name = node.name

        self.log.info("Registering node {name} [{nodeid}], "
                      "type {module}, host {hostname} [{hostid}], "
                      "{n_e} events, {n_c} commands from {ip}",
                      name=node.name,
                      nodeid=node.nodeid,
                      hostname=node.hostname,
                      hostid=node.hostid,
                      module=node.module,
                      ip=node.peer,
                      n_e=len(params.get('events')),
                      n_c=len(params.get('commands')),
                     )

        # -- Known node?
        if name in self.nodes:

            # The other node is still active, so refuse registration
            other = self.nodes[name]
            if other.connected:
                raise NodeRegistrationException(
                    'Node already taken by host %s [%s]' %(
                        other.hostname, other.hostid))

        # -- Register the new node
        self.nodes[name] = node

        # -- Register node events
        evlist = [name + '/' + e for e in params.get('events', [])]
        node.events = tuple(evlist)
        self.add_events(evlist)

        # -- Register node commands
        evlist = [name + '/' + e for e in params.get('commands', [])]
        node.commands = tuple(evlist)

        # Here is the magic for connecting the remote node commands to the
        # server's command dict. Each node command will get an entry which
        # will use LuminaProtocol.send(). This function will simply
        # send the request to the node and return a deferred for the reply
        self.add_commands({e: node.send for e in evlist})

        # Return success
        return None


    def update_status(self, status):  # pylint: disable=W0613
        ''' Status update callback '''
        l = [node.status for node in compat_itervalues(self.nodes)]
        l += [node.link for node in compat_itervalues(self.nodes)]
        (state, why) = ColorState.combine(*l)
        self.node_status.set(state, why)


    def run_command(self, message, fail_on_unknown=True):
        ''' Run a command and return reply or a deferred object for later reply '''

        def unknown_command(message):
            ''' Handle unknown commands gracefully '''
            if fail_on_unknown:
                raise UnknownCommandException(message.name)
            self.log.warn("Ignoring unknown command: '{n}'", n=message.name)

        # -- Run the named fn from the self.commands dict
        return self.commands.get(message.name, unknown_command)(message)


    def add_commands(self, commands):
        ''' Add to the dict of known commands and register their callback fns '''
        self.log.info("Registering {n} commands", n=len(commands))
        for name, fn in commands.items():
            self.log.debug("  + {n}", n=name)
            if name in self.commands:
                raise NodeConfigException("Duplicate command '{n}'".format(n=name))
            self.commands[name] = fn


    def remove_commands(self, commands):
        ''' Remove from the dict of known commands '''
        self.log.info("Removing {n} commands", n=len(commands))
        for name in commands:
            self.log.debug("  - {n}", n=name)
            del self.commands[name]


    def add_events(self, events):
        ''' Add to the list of known events'''
        self.log.info("Registering {n} events", n=len(events))
        for name in events:
            self.log.debug("  + {n}", n=name)
            if name in self.events:
                raise NodeConfigException("Duplicate event '{n}'".format(n=name))
            self.events.append(name)


    def remove_events(self, events):
        ''' Remove from the list of known events'''
        self.log.info("Removing {n} events", n=len(events))
        for name in events:
            self.log.debug("  - {n}", n=name)
            self.events.remove(name)


    def get_info(self):
        ''' Return a dict of info about this server '''
        return {
            'nodes'       : [{
                'name'         : node.name,
                'nodeid'       : node.nodeid,
                'hostname'     : node.hostname,
                'hostid'       : node.hostid,
                'module'       : node.module,
                'sequence'     : node.sequence,
                'status'       : node.status.state,
                'status_why'   : node.status.why,
                'link'         : node.link.state,
                'link_why'     : node.link.why,
                'commands'     : node.commands,
                'events'       : node.events,
                'connected'    : node.connected,
                'lastactivity' : node.lastactivity.isoformat()+'Z',
            } for node in compat_itervalues(self.nodes)],
            'n_commands'  : len(self.commands),
            'n_events'    : len(self.events),
            'status'      : str(self.status),
            'status_why'  : str(self.status.why),
            'node_status' : str(self.node_status),
            'node_status_why' : str(self.node_status.why),
        }



PLUGIN = Server

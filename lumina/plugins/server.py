# -*- python -*-
from __future__ import absolute_import

from datetime import datetime

from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.internet.task import LoopingCall

from lumina.plugin import Plugin
from lumina.exceptions import (NodeConfigException, UnknownCommandException,
                               UnknownMessageException)
from lumina.log import Logger
from lumina.protocol import LuminaProtocol
from lumina.state import ColorState
from lumina.message import Message
from lumina.lumina import master


# FIXME: Add this as a config statement

# Timeout before a node is considered dead and will be disconnected. Should be
# a longer interval than the nodes keepalive interval.
NODE_TIMEOUT = 180


# To connect interactively to the server use:
#    socat - TCP:127.0.0.1:8081


class ServerProtocol(LuminaProtocol):
    node_timeout = NODE_TIMEOUT


    def __init__(self, parent):
        LuminaProtocol.__init__(self, parent)
        self.servername = parent.name

        # Must have new logger as we change the namespace for it when
        # clients register a node name
        self.log = Logger(namespace=self.servername)

        # Default node data
        self.sequence = None
        self.nodeid = None
        self.hostname = None
        self.hostid = None
        self.module = None
        self.status = ColorState(log=self.log)
        self.status.add_callback(self.parent.update_status, run_now=True)
        self.link.add_callback(self.parent.update_status, run_now=True)
        self.commands = []
        self.events = []
        self.lastactivity = datetime.utcnow()
        self.connected = False


    def connectionMade(self):
        LuminaProtocol.connectionMade(self)

        self.log.namespace = self.servername + ':' + self.peer
        self.log.info("Connect from {ip}", ip=self.peer, system=self.servername)

        self.hostname = self.peer
        self.connected = True

        # -- Setup a keepalive timer ensuring we have connection with the node
        #    LuminaProtocol will handle resetting and stopping it on data
        #    reception and disconnect.
        self.keepalive = LoopingCall(self.connectionTimeout)
        self.keepalive.start(self.node_timeout, False)

        # Register with parent class
        self.parent.add_connection(self)


    def connectionLost(self, reason):
        self.log.info("Lost connection from '{n}' ({ip})", n=self.name, ip=self.peer)
        LuminaProtocol.connectionLost(self, reason)

        self.connected = False
        self.status.set_OFF()

        # Unregister parent class
        self.parent.remove_connection(self)


    def connectionTimeout(self):
        self.log.info("Communication timeout from '{n}' ({ip})", n=self.name, ip=self.peer)
        self.transport.loseConnection()


    def messageReceived(self, message):
        ''' Handle messages from nodes '''

        cmd = message.name


        # -- Command type
        if message.is_type('command'):

            # -- Register node name
            if cmd == 'register':

                # Register with the server
                result = self.parent.register_node(self, message.args[0])
                if result:
                    self.log.error('Node registration failed: {e}', e=result)
                    return result

                # Set logging name
                self.log.namespace = self.servername + ':' + self.name

                # Respond to the node if the node registration was successful
                return None

            # -- Handle status update
            elif cmd == 'status':

                # Not really interested in the old state in message.args[1]?
                self.status.set(message.args[0], why=message.args[2])
                return None

            # -- General commands
            #
            # Note that this command will be called on non-existing commmands
            # which is intended behaviour.
            return self.parent.run_command(message)


        # -- Event type
        elif message.is_type('event'):

            prefix = self.name + '/'

            # -- Check that the event is valid and registred
            if not cmd.startswith(prefix):
                self.log.error("Ignoring undeclared event '{m}'", m=message)
                return None

            cmd = cmd.replace(prefix,'')
            if cmd not in self.parent.events:
                self.log.error("Ignoring undeclared event '{m}'", m=message)
                return None

            # -- A new incoming event. Plainly accept it without checking
            #    self.parent.events
            return self.parent.handle_event(message)


        # -- Unknown message type
        else:
            self.log.error("Unexpectedly received message {m}", m=message)
            raise UnknownMessageException("Unknown message type: '%s'" %(message.type,))



class ServerFactory(Factory):
    noisy = False

    def __init__(self, parent):
        self.parent = parent
        self.name = parent.name

    def buildProtocol(self, addr):
        return ServerProtocol(parent=self.parent)

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
            '_info': lambda a: master.get_info(),
            '_server': lambda a: self.get_info(),
        }


    def setup(self):

        # -- Config options
        self.port = master.config.get('port')
        self.nodelist = master.config.get('nodes', name=self.name)

        # -- List of server commands and events
        self.events = []
        self.commands = {}
        self.add_commands(self.server_commands)

        # -- List of connections
        self.connections = []
        self.sequence = 0

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

        self.factory = ServerFactory(parent=self)
        reactor.listenTCP(self.port, self.factory)


    def run_command(self, message, fail_on_unknown=True):
        ''' Run a command and return reply or a deferred object for later reply '''

        def unknown_command(message):
            exc = UnknownCommandException(message.name)
            message.set_fail(exc)
            if fail_on_unknown:
                self.log.error('', cmderr=message)
                raise exc
            self.log.warn("Ignoring unknown command: '{n}'", n=message.name)

        # -- Run the named fn from the self.commands dict
        return self.commands.get(message.name, unknown_command)(message)


    # --- INTERNAL COMMANDS
    def update_status(self, status):  # pylint: disable=unused-variable
        l = [node.status for node in self.nodes.itervalues()]
        l += [node.link for node in self.nodes.itervalues()]
        (state, why) = ColorState.combine(*l)
        self.node_status.set(state, why)


    def add_connection(self, node):
        ''' Register the connected node '''
        self.connections.append(node)
        self.sequence += 1
        node.sequence = self.sequence
        self.status.set_GREEN()


    def remove_connection(self, node):
        ''' Remove the disconnected node '''
        self.connections.remove(node)
        if not self.connections:
            self.status.set_YELLOW('No nodes connected')

        if node.events:
            self.remove_events(node.events)
            node.events = []

        if node.commands:
            self.remove_commands(node.commands)
            node.commands = []


    def register_node(self, node, params):
        ''' Check and register a node. '''

        # -- Transfer parameters to node
        name = params.get('node')
        node.name = name
        node.status.name = name
        node.link.name = name
        node.nodeid = params.get('nodeid')
        node.hostname = params.get('hostname')
        node.hostid = params.get('hostid')
        node.module = params.get('module')

        self.log.info("Registering node {name} [{nodeid}], "
                      "type {module}, host {hostname} [{hostid}], "
                      "{n_e} events, {n_c} commands from {ip}",
                      name=name,
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
                return 'Node already taken by host %s [%s]' %(other.hostname, other.hostid)

        # -- Register the new node
        self.nodes[name] = node

        # -- Register node events
        evlist = [node.name + '/' + e for e in params.get('events', [])]
        node.events = tuple(evlist)
        self.add_events(evlist)

        # -- Register node commands
        evlist = [node.name + '/' + e for e in params.get('commands', [])]
        node.commands = tuple(evlist)

        # Here is the magic for connecting the remote node commands to the
        # server's command dict. Each node command will get an entry which
        # will use LuminaProtocol.send(). This function will simply
        # send the request to the node and return a deferred for the reply
        self.add_commands({e: node.send for e in evlist})

        # Return success
        return None


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
                'seqence'      : node.sequence,
                'status'       : node.status.state,
                'status_why'   : node.status.why,
                'link'         : node.link.state,
                'link_why'     : node.link.why,
                'commands'     : node.commands,
                'events'       : node.events,
                'connected'    : node.connected,
                'lastactivity' : node.lastactivity.isoformat()+'Z',
            } for node in self.nodes.itervalues()],
            'n_commands'  : len(self.commands),
            'n_events'    : len(self.events),
            'status'      : str(self.status),
            'status_why'  : str(self.status.why),
            'node_status' : str(self.node_status),
            'node_status_why' : str(self.node_status.why),
        }



PLUGIN = Server

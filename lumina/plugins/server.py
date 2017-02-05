# -*- python -*-
from __future__ import absolute_import

from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.internet.defer import maybeDeferred

from lumina.plugin import Plugin
from lumina.exceptions import (NodeConfigException, UnknownCommandException)
from lumina.log import Logger
from lumina.protocol import LuminaProtocol


# To connect interactively to the server use:
#    socat - TCP:127.0.0.1:8081


class ServerProtocol(LuminaProtocol):

    def __init__(self, parent):
        LuminaProtocol.__init__(self, parent)
        self.servername = parent.name

        # Must have new logger as we change the namespace for it when
        # clients register a node name
        self.log = Logger(namespace=self.servername)


    def connectionMade(self):
        LuminaProtocol.connectionMade(self)

        self.log.namespace = self.servername + ':' + self.peer
        self.log.info("Connect from {ip}", ip=self.peer, system=self.servername)

        # Node data
        self.nodeid = None
        self.hostname = self.peer
        self.hostid = None
        self.module = None
        self.status = 'OFF'
        self.status_why = 'No data received yet'
        self.n_commands = 0
        self.n_events = 0

        self.events = []
        self.commands = []

        # Inform parent class
        self.parent.add_node(self)


    def connectionLost(self, reason):
        self.log.info("Lost connection from '{n}' ({ip})", n=self.name, ip=self.peer)
        LuminaProtocol.connectionLost(self, reason)

        # Inform parent class
        self.parent.remove_node(self)


    def eventReceived(self, event):
        ''' Handle messages from nodes '''

        # Currently this treats everything as events coming from a client,
        # however if event.seq is not None, then this is a command requesting
        # a reply

        # -- Register node name
        if event.name == 'register':

            # Extract the data
            kw = event.kw
            self.name = kw.get('node', self.name)
            self.nodeid = kw.get('nodeid', self.nodeid)
            self.hostname = kw.get('hostname', self.hostname)
            self.hostid = kw.get('hostid', self.hostid)
            self.module = kw.get('module', self.module)
            self.events = kw.get('events', [])
            self.commands = kw.get('commands', [])

            # Register with the server (which might change our name)
            self.parent.register_node(self)

            # Set logging name
            self.log.namespace = self.servername + ':' + self.name

            return

        # -- Handle status update
        elif event.name == 'status':
            self.status = event.args[0]
            self.status_why = event.args[2]
            return

        # -- Handle event
        elif event.name == 'serverid':
            return (self.parent.hostid,)

        # -- A new incoming event.
        elif event.name in self.parent.events:
            return self.parent.handle_event(event)

        # -- A new command
        elif event.name in self.parent.commands:
            # Must make a new event for the command and pass that
            # defer back to the calling command
            newevent = event.copy()
            return self.parent.run_command(newevent)

        # -- An unknown event, but let's send it to the event handler
        else:
            return self.parent.handle_event(event)



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

    name = 'SERVER'

    CONFIG = {
        'port': dict(default=5326, help='Hosting server port', type=int),
    }


    def setup(self, main):
        Plugin.setup(self, main)

        # Config options
        self.port = main.config.get('port', name=self.name)

        # Store name for main instance. Used by web and admin to retrieve
        #self.hostname = main.hostname
        self.hostid = main.hostid

        # List of commands and events
        self.events = []
        self.commands = {}

        # List of connected nodes
        self.nodes = []
        self.sequence = 0

        # Setup default do-nothing handler for the incoming events
        self.handle_event = lambda a: self.log.info("Ignoring event '{a}'", a=a)

        self.factory = ServerFactory(parent=self)
        reactor.listenTCP(self.port, self.factory)


    def run_command(self, event, fail_on_unknown=True):
        ''' Send a command to a node and return a deferred object for the reply '''

        def unknown_command(event):
            exc = UnknownCommandException(event.name)
            event.set_fail(exc)
            if fail_on_unknown:
                self.log.error('', cmderr=event)
                raise exc
            self.log.warn("Ignoring unknown command: '{n}'", n=event.name)

        return maybeDeferred(self.commands.get(event.name, unknown_command), event)


    # --- INTERNAL COMMANDS
    def add_node(self, node):
        ''' Register the connected node '''
        self.sequence += 1
        node.sequence = self.sequence
        self.nodes.append(node)
        self.status.set_GREEN('%s nodes connected' %(len(self.nodes)))


    def remove_node(self, node):
        ''' Remove the disconnected node '''
        self.nodes.remove(node)
        if not self.nodes:
            self.status.set_YELLOW('No nodes connected')
        else:
            self.status.set_GREEN('%s nodes connected' %(len(self.nodes)))

        if node.events:
            self.remove_events(node.events)

        if node.commands:
            self.remove_commands(node.commands)


    def register_node(self, node):
        ''' Check and register a node. '''

        self.log.info("Registering node {node} [{nodeid}], "
                      "type {module}, host {hostname} [{hostid}], "
                      "{n_e} events, {n_c} commands from {ip}",
                      node=node.name,
                      nodeid=node.nodeid,
                      hostname=node.hostname,
                      hostid=node.hostid,
                      module=node.module,
                      ip=node.peer,
                      n_e=len(node.events),
                      n_c=len(node.commands))

        # -- Check the node id from the other nodes connected
        nodeid = node.nodeid
        nodelist = [n.nodeid == nodeid for n in self.nodes if n != node]
        if any(nodelist):
            self.log.warn("Node {n} [{id}] is already connected. "
                          "Possible reconnect", n=node.name, id=nodeid)

            # FIXME: disconnect the double node, because the name, event and
            #        commands probably fail to register.

        # -- Set the node name
        name = self.check_node_name(node, node.name)
        if name != node.name:
            self.log.warn("Node '{o}' is taken, renaming to '{n}'", o=node.name, n=name)
        node.name = name

        # -- Register node event
        evlist = [node.name + '/' + e for e in node.events]
        if evlist:
            node.events = tuple(evlist)
            self.add_events(evlist)

        # -- Register node commands
        evlist = [node.name + '/' + e for e in node.commands]
        if evlist:
            node.commands = tuple(evlist)
            self.add_commands({e: node.request_raw for e in evlist})


    def check_node_name(self, node, name):
        newname = name
        for count in range(1, 10):
            names = [n.name == newname for n in self.nodes if n != node]
            if not any(names):
                return newname
            newname = name + '_' + str(count)
        raise NodeConfigException("Unable to find appropriate name for '{o}'".format(o=name))


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


PLUGIN = Server

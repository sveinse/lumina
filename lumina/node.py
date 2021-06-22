#-*- python -*-
""" Base class for node plugins. Client-side communication functions. """
from __future__ import absolute_import, division, print_function

import os
try:
    from queue import Queue, Empty
except ImportError:
    # Py2
    from Queue import Queue, Empty
from binascii import hexlify

from twisted.internet.defer import Deferred
from twisted.internet.defer import inlineCallbacks
from twisted.internet.protocol import ReconnectingClientFactory

from lumina.plugin import Plugin
from lumina.message import Message
from lumina.exceptions import (UnknownCommandException, UnknownMessageException)
from lumina.protocol import LuminaProtocol



class NodeProtocol(LuminaProtocol):
    ''' Node communication protocol '''

    def connectionMade(self):
        LuminaProtocol.connectionMade(self)
        self.parent.connectionMade(self)

    def connectionLost(self, reason):
        LuminaProtocol.connectionLost(self, reason)
        self.parent.connectionLost(self, reason)

    def messageReceived(self, message):
        return self.parent.messageReceived(self, message)



class NodeFactory(ReconnectingClientFactory):
    ''' Factory generator for the NodeProtocol. Uses reconnection to ensure
        that the Node always retries connection until a connection is made.
    '''
    noisy = False
    maxDelay = 10
    factor = 1.6180339887498948

    def __init__(self, parent):
        self.parent = parent
        self.log = parent.log
        self.sequence = 1

    def buildProtocol(self, addr):
        self.resetDelay()
        protocol = NodeProtocol(parent=self.parent, sequence=self.sequence)
        self.sequence += 1
        return protocol

    def clientConnectionLost(self, connector, reason):
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        self.log.error('Node server connect failed: {e}', e=reason.getErrorMessage())
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)



class Node(Plugin):
    ''' Node objects for plugins '''

    # Setup no events and comands by default
    events = {}
    commands = {}

    # Endpoint configuration options
    GLOBAL_CONFIG = {
        'port'  : dict(default=5326, help='Lumina port to connect to', type=int),
        'server': dict(default='localhost', help='Lumina server to connect to'),
    }

    # Override the list of configure methods from the Plugin
    CONFIGURE_METHODS = ('configure', 'node_configure', 'node_setup', 'setup')


    def node_configure(self):
        ''' Configure the node '''

        self.node_commands = {
            '_info': lambda a: self.master.get_info(),
        }

        self.commands.update(self.node_commands)


    def node_setup(self):
        ''' Setup the node '''

        self.serverhost = self.master.config.get('server')
        self.serverport = self.master.config.get('port')
        self.nodeid = hexlify(os.urandom(3))

        self.node_protocol = None
        self.node_active = False
        self.node_queue = Queue()

        # -- Connect to the server
        self.node_factory = NodeFactory(parent=self)
        self.log.info("Connecting to server on {h}:{p}", h=self.serverhost,
                      p=self.serverport)
        self.master.reactor.connectTCP(self.serverhost,
                                       self.serverport,
                                       self.node_factory)


    def close(self):
        ''' Close the connection '''
        Plugin.close(self)
        if self.node_protocol:
            self.node_protocol.transport.loseConnection()


    @inlineCallbacks
    def connectionMade(self, node):
        ''' Handle connection event from node '''
        self.log.info("Connected to {ip}", ip=node.peer)

        # -- Set name and node
        node.name = self.name
        self.node_protocol = node
        self.node_active = False

        # -- Register device
        data = dict(node=self.name,
                    nodeid=self.nodeid,
                    hostname=self.master.hostname,
                    hostid=self.master.hostid,
                    module=self.module,
                    events=self.events,
                    commands=self.commands.keys(),
                   )
        self.log.info("Registering node {node} [{nodeid}], "
                      "type {module}, host {hostname} [{hostid}], "
                      "{n_e} events, {n_c} commands",
                      n_e=len(self.events),
                      n_c=len(self.commands),
                      **data)
        try:
            yield node.send(Message.create('command', 'register', data))
        except Exception as failure:
            self.log.error("Node registration FAILED: {f}", f=failure)
            node.transport.loseConnection()
            return

        self.log.info("Node registration SUCCESS")

        # -- Enable sending of events from the parent class
        self.node_active = True

        # -- Subscribe to the change of state by sending status back to server
        #    Send the update now
        def send_status(status):
            ''' Status update callback. Only send updates if connected '''
            if self.node_active:
                self.send(Message.create('command', 'status', status.state,
                                         status.old, status.why))
        self.status.add_callback(send_status, run_now=True)

        # -- Flush any queue that might have been accumulated before
        #    connecting to the controller
        self.sendQueue()
        

    def connectionLost(self, node, reason):
        self.log.info("Lost node server connection to {ip}: {r}",
            ip=node.peer, r=reason)

        # This will cause queuing of commands
        self.node_active = False
        self.node_protocol = None


    def messageReceived(self, node, message):
        ''' Handle message from server '''
        
        # Remove the plugin prefix from the name
        prefix = node.name + '/'
        cmd = message.name.replace(prefix, '')

        # -- Command type
        if message.is_type('command'):

            def unknown_command(message):
                ''' Placeholder fn for unknown commands '''
                raise UnknownCommandException(message.name)

            # -- Run the named fn from the commands dict
            return self.commands.get(cmd, unknown_command)(message)

        # -- Unknown message type
        else:
            self.log.error("Unexpectedly received message {m}", m=message)
            raise UnknownMessageException("Unknown message type: '%s'" %(message.type,))
 

    # -- Commands to communicate with server
    def send(self, message):
        ''' Send a message to the node protocol. If the node is not connected queue
            the message.
        '''

        # The function to send the data to the server
        # pylint: disable=unnecessary-lambda
        sendfn = lambda ev: self.node_protocol.send(ev)

        if self.node_active:
            # If the protocol is avaible, simply call the function
            # It will return a deferred for us.
            return sendfn(message)

        # Create a defer object for the future reply
        defer = Deferred()
        self.node_queue.put((defer, sendfn, message))

        self.log.info("{e}  --  Not connected to server, "
                      "queueing. {n} items in queue",
                      e=message, n=self.node_queue.qsize())

        return defer


    def sendQueue(self):
        ''' (Attempt to) send the accumulated queue to the protocol. '''

        qsize = self.node_queue.qsize()
        if not self.node_active or not qsize:
            return

        self.log.info("Flushing queue of {n} items...", n=qsize)

        try:
            while True:
                (defer, sendfn, message) = self.node_queue.get(False)
                self.log.info("Sending {e}", e=message)
                result = sendfn(message)
                if isinstance(result, Deferred):
                    # Ensure that when the result object fires that the
                    # defer object also fire
                    result.chainDeferred(defer)
                else:
                    defer.callback(result)
        except Empty:
            pass


    # -- Helper functions
    def sendEvent(self, name, *args):
        ''' Send event to server. '''
        # The events must be prefixed by its node name before being
        # dispatched to the server
        return self.send(Message.create('event', self.name + '/' + name, *args))

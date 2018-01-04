#-*- python -*-
""" Base class for node plugins. Client-side communication functions. """
from __future__ import absolute_import

import os
from Queue import Queue, Empty
from binascii import hexlify

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet.task import LoopingCall

from lumina.plugin import Plugin
from lumina.message import Message
from lumina.exceptions import (UnknownCommandException, UnknownMessageException)
from lumina.protocol import LuminaProtocol
from lumina.lumina import master

# FIXME: Add this as a config statement

# The interval to send empty messages to server to keep the link alive
KEEPALIVE_INTERVAL = 60


class NodeProtocol(LuminaProtocol):
    ''' Node communication protocol '''
    keepalive_interval = KEEPALIVE_INTERVAL


    def connectionMade(self):
        LuminaProtocol.connectionMade(self)
        self.log.info("Connected to {ip}", ip=self.peer)

        # -- Update protocol variables
        self.name = self.parent.name

        # -- Link this protocol to the parent
        self.parent.node_protocol = self
        self.parent.node_connected = False

        # -- Setup a keepalive timer (not yet activated)
        #    LuminaProtocol will handle resetting and stopping it on data
        #    reception and disconnect.
        self.keepalive = LoopingCall(self.transport.write, '\n')

        # -- List of commands plus additional internal commands
        commands = self.parent.commands.keys()
        commands += ['_info']

        # -- Register device
        data = dict(node=self.parent.name,
                    nodeid=self.parent.nodeid,
                    hostname=master.hostname,
                    hostid=master.hostid,
                    module=self.parent.module,
                    events=self.parent.events,
                    commands=commands,
                   )
        self.log.info("Registering node {node} [{nodeid}], "
                      "type {module}, host {hostname} [{hostid}], "
                      "{n_e} events, {n_c} commands",
                      n_e=len(self.parent.events),
                      n_c=len(self.parent.commands),
                      **data)
        defer = self.send(Message.create('command', 'register', data))
        defer.addCallback(self.registered)
        defer.addErrback(self.registerError)


    def registerError(self, failure):
        ''' Handle server-side registration error. The server has issued
            an exception at this point.
        '''
        self.log.error("Node registration FAILED: {f}", f=failure)
        self.transport.loseConnection()

        # FIXME: Should we give up the retry connect mechanism?
        #self.parent.node_factory.stopTrying()


    def registered(self, result):  # pylint: disable=W0613
        ''' Handle registration response '''

        self.log.info("Node registration SUCCESS")

        # -- Start the keepalive pings
        self.keepalive.start(self.keepalive_interval, False)

        # -- Send status
        # The parent class will send update on changes, but in case of
        # reconnect, a new update must be pushed
        # Equal value on state and old state indicates a refresh, not
        # new value.
        self.send(Message.create('command', 'status',
                                 self.parent.status.state,
                                 self.parent.status.state,
                                 self.parent.status.why))

        # -- Enable sending of events from the parent class
        self.parent.node_connected = True

        # -- Flush any queue that might have been accumulated before
        #    connecting to the controller
        self.parent.sendQueue()


    def connectionLost(self, reason):
        self.log.info("Lost node server connection to {ip}", ip=self.peer)
        LuminaProtocol.connectionLost(self, reason)

        # This will cause the parent to queue new commands
        self.parent.node_connected = False
        self.parent.node_protocol = None


    def messageReceived(self, message):
        ''' Handle message from server '''

        # Remove the plugin prefix from the name
        prefix = self.name + '/'
        cmd = message.name.replace(prefix, '')

        # -- Command type
        if message.is_type('command'):

            # -- Handle the internal commands
            if cmd == '_info':
                return master.get_info()

            # -- All other requests to nodes are commands handled by
            #    the Node parent

            def unknown_command(message):
                ''' Placeholder fn for unknown commands '''
                exc = UnknownCommandException(message.name)
                message.set_fail(exc)
                self.log.error('NODE {_cmderr}', cmderr=message)
                raise exc

            # -- Run the named fn from the commands dict
            return self.parent.commands.get(cmd, unknown_command)(message)


        # -- Unknown message type
        else:
            self.log.error("Unexpectedly received message {m}", m=message)
            raise UnknownMessageException("Unknown message type: '%s'" %(message.type,))



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

    def buildProtocol(self, addr):
        self.resetDelay()
        return NodeProtocol(parent=self.parent)

    def clientConnectionLost(self, connector, reason):
        #self.log.info(reason.getErrorMessage())
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
    CONFIGURE_METHODS = ('configure', 'node_setup', 'setup')


    def node_setup(self):
        ''' Setup the node '''

        self.serverhost = master.config.get('server')
        self.serverport = master.config.get('port')
        self.nodeid = hexlify(os.urandom(3))

        self.node_protocol = None
        self.node_connected = False
        self.node_queue = Queue()

        # Subscribe to the change of state by sending status back to server
        def send_status(status):
            ''' Status update callback. Only send updates if connected '''
            if self.node_connected:
                self.send(Message.create('command', 'status', status.state,
                                         status.old, status.why))
        self.status.add_callback(send_status)

        self.node_factory = NodeFactory(parent=self)
        reactor.connectTCP(self.serverhost, self.serverport, self.node_factory)


    def close(self):
        Plugin.close(self)
        if self.node_protocol:
            self.node_protocol.transport.loseConnection()


    # -- Commands to communicate with server
    def send(self, message):
        ''' Send a message to the node protocol. If the node is not connected queue
            the message.
        '''

        # The function to send the data to the server
        # pylint: disable=unnecessary-lambda
        sendfn = lambda ev: self.node_protocol.send(ev)

        if self.node_connected:
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
        if not self.node_connected or not qsize:
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

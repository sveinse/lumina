#-*- python -*-
from __future__ import absolute_import

import os
from Queue import Queue, Empty
from binascii import hexlify

from twisted.internet import reactor
from twisted.internet.defer import Deferred #, maybeDeferred
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet.task import LoopingCall

from lumina.plugin import Plugin
from lumina.event import Event
from lumina.exceptions import UnknownCommandException
from lumina.protocol import LuminaProtocol

# FIXME: Add this as a config statement

# The interval to send empty messages to server to keep the link alive
KEEPALIVE_INTERVAL = 60


class NodeProtocol(LuminaProtocol):
    keepalive_interval = KEEPALIVE_INTERVAL


    def connectionMade(self):
        LuminaProtocol.connectionMade(self)
        self.log.info("Connected to {ip}", ip=self.peer)

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
                    hostname=self.parent.hostname,
                    hostid=self.parent.hostid,
                    module=self.parent.module,
                    events=self.parent.events,
                    commands=commands)
        self.log.info("Registering node {node} [{nodeid}], "
                      "type {module}, host {hostname} [{hostid}], "
                      "{n_e} events, {n_c} commands",
                      n_e=len(self.parent.events),
                      n_c=len(self.parent.commands),
                      **data)
        defer = self.request('register', **data)
        defer.addCallback(self.registered)
        defer.addErrback(self.registerError)


    def registerError(self, err):
        ''' Handle server-side registration error. The server has issued
            an exception at this point.
        '''
        self.log.error("Node registration FAILED: {err}", err=err)
        self.transport.loseConnection()

        # FIXME: Should we give up the retry connect mechanism?
        #self.parent.node_factory.stopTrying()


    def registered(self, arg):
        ''' Handle registration response '''

        # Give up the connection if the response is rejected
        if arg.result:
            self.registerError(arg.result)
            return

        self.log.info("Node registration SUCCESS")

        # -- Start the keepalive pings
        self.keepalive.start(self.keepalive_interval, False)

        # -- Send status
        # The parent class will send update on changes, but in case of
        # reconnect, a new update must be pushed
        # Equal value on state and old state indicates a refresh, not
        # new value.
        self.emit('status', self.parent.status.state,
                  self.parent.status.state, self.parent.status.why)

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


    def commandReceived(self, event):
        ''' Handle commands from server '''

        # Remove the plugin prefix from the name
        prefix = self.parent.name + '/'
        cmd = event.name.replace(prefix, '')

        # -- Handle the internal commands
        if cmd == '_info':
            return self.parent.main.get_info()

        # -- All other requests to nodes are commands
        else:
            return self.parent.run_command(event)



class NodeFactory(ReconnectingClientFactory):
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


    def setup(self, main):
        Plugin.setup(self, main)

        self.main = main    # The _info command requires access to main
        self.serverhost = main.config.get('server')
        self.serverport = main.config.get('port')
        self.hostname = main.hostname
        self.hostid = main.hostid
        self.nodeid = hexlify(os.urandom(3))

        self.node_protocol = None
        self.node_connected = False
        self.node_queue = Queue()

        # Subscribe to the change of state by sending status back to server
        def emit_status(status):
            ''' Status update callback. Only send updates if connected '''
            if self.node_connected:
                self.emit_raw(Event('status', status.state, status.old, status.why))
        self.status.add_callback(emit_status)

        self.node_factory = NodeFactory(parent=self)
        reactor.connectTCP(self.serverhost, self.serverport, self.node_factory)


    def run_command(self, event, fail_on_unknown=True):
        ''' Run a command and return reply or a deferred object for later reply '''

        # Remove the plugin prefix from the name
        prefix = self.name + '/'
        name = event.name.replace(prefix, '')

        def unknown_command(event):
            ''' Placeholder fn for unknown commands '''
            exc = UnknownCommandException(event.name)
            event.set_fail(exc)
            if fail_on_unknown:
                self.log.error('NODE', cmderr=event)
                raise exc
            self.log.warn("Ignoring unknown command: '{n}'", n=event.name)

        # -- Run the named fn from the self.commands dict

        # FIXME: The maybeDeferred() is possibly not needed here
        #return maybeDeferred(self.commands.get(name, unknown_command), event)
        return self.commands.get(name, unknown_command)(event)


    # -- Commands to communicate with server
    def emit(self, name, *args, **kw):
        ''' Emit an event and send to server. Append the prefix for this
            node '''
        return self.emit_raw(Event(self.name + '/' + name, *args, **kw))

    def emit_raw(self, event):
        ''' Send an event to server. An event does not expect a reply '''
        return self.sendServer(event, lambda ev: self.node_protocol.emit_raw(ev))

    def request(self, name, *args, **kw):
        return self.request_raw(Event(name, *args, **kw))

    def request_raw(self, event):
        ''' Send a request to server. A request expects a reply '''
        return self.sendServer(event, lambda ev: self.node_protocol.request_raw(ev))


    def sendServer(self, event, protofn):
        ''' Send a message to the node protocol. If the node is not connected queue
            the message.
        '''

        if self.node_connected:
            # If the protocol is avaible, simply call the function
            # It will return a deferred for us.
            return protofn(event)

        # Create a defer object for the future reply
        defer = Deferred()
        self.node_queue.put((defer, protofn, event))

        self.log.info("{e}  --  Not connected to server, "
                      "queueing. {n} items in queue",
                      e=event, n=self.node_queue.qsize())

        return defer


    def sendQueue(self):
        ''' (Attempt to) send the accumulated queue to the protocol. '''

        qsize = self.node_queue.qsize()
        if not self.node_connected or not qsize:
            return

        self.log.info("Flushing queue of {n} items...", n=qsize)

        try:
            while True:
                (defer, protofn, event) = self.node_queue.get(False)
                self.log.info("Sending {e}", e=event)
                result = protofn(event)
                if isinstance(result, Deferred):
                    # Ensure that when the result object fires that the
                    # defer object also fire
                    result.chainDeferred(defer)
                else:
                    defer.callback(result)
        except Empty:
            pass

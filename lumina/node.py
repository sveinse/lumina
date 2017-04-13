#-*- python -*-
from __future__ import absolute_import

import os
from Queue import Queue, Empty
from binascii import hexlify

from twisted.internet import reactor
from twisted.internet.defer import maybeDeferred, Deferred
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet.task import LoopingCall

from lumina.plugin import Plugin
from lumina.event import Event
from lumina.exceptions import UnknownCommandException
from lumina.protocol import LuminaProtocol



class NodeProtocol(LuminaProtocol):


    def connectionMade(self):
        LuminaProtocol.connectionMade(self)
        self.log.info("Connected to {ip}", ip=self.peer)

        # -- Give our handle to the parent node class
        self.parent.protocol = self

        # -- Keepalive pings
        self.keepalive = LoopingCall(self.transport.write, '\n')
        self.keepalive.start(60, False)

        # -- Register device
        data = dict(node=self.parent.name,
                    nodeid=self.parent.nodeid,
                    hostname=self.parent.hostname,
                    hostid=self.parent.hostid,
                    module=self.parent.module,
                    events=self.parent.events,
                    commands=self.parent.commands.keys())
        self.log.info("Registering node {node} [{nodeid}], "
                      "type {module}, host {hostname} [{hostid}], "
                      "{n_e} events, {n_c} commands",
                      n_e=len(self.parent.events),
                      n_c=len(self.parent.commands),
                      **data)
        self.emit('register', **data)

        # -- Send status
        # The parent class will send update on changes, but in case of
        # reconnect, a new update must be pushed
        self.emit('status', self.parent.status.state,
                  self.parent.status.state, self.parent.status.why)

        # -- Flush any queue that might have been accumulated before
        #    connecting to the controller
        self.parent.sendQueue()


    def connectionLost(self, reason):
        self.log.info("Lost connection with {ip}", ip=self.peer)
        LuminaProtocol.connectionLost(self, reason)

        # This will cause the parent to queue new commands
        self.parent.protocol = None
        self.keepalive.stop()


    def eventReceived(self, event):
        ''' Process an incoming event or command '''

        # -- All new requests to nodes are commands
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
        self.log.error('Server connect failed: {e}', e=reason.getErrorMessage())
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)



class Node(Plugin):
    ''' Node objects for plugins '''

    # Setup no events and comands by default
    events = {}
    commands = {}

    # Endpoint configuration options
    CONFIG = {
        'port'  : dict(common=True, default=5326, help='Port to connect to', type=int),
        'server': dict(common=True, default='localhost', help='Server to connect to'),
    }


    def setup(self, main):
        Plugin.setup(self, main)

        # Subscribe to the change of state by sending status back to server
        self.status.add_callback(self.emit_status)

        self.host = main.config.get('server')
        self.port = main.config.get('port')
        self.hostname = main.hostname
        self.hostid = main.hostid
        self.nodeid = hexlify(os.urandom(4))

        self.protocol = None
        self.queue = Queue()

        self.factory = NodeFactory(parent=self)
        reactor.connectTCP(self.host, self.port, self.factory)


    def run_command(self, event, fail_on_unknown=True):
        ''' Run a command and return a deferred object for the reply '''

        # Remove the plugin prefix from the name
        prefix = self.name + '/'
        name = event.name.replace(prefix, '')

        def unknown_command(event):
            exc = UnknownCommandException(event.name)
            event.set_fail(exc)
            if fail_on_unknown:
                self.log.error('NODE', cmderr=event)
                raise exc
            self.log.warn("Ignoring unknown command: '{n}'", n=event.name)

        return maybeDeferred(self.commands.get(name, unknown_command), event)


    # -- Commands to communicate with server
    def emit(self, name, *args, **kw):
        ''' Emit an event and send to server '''
        return self.emit_raw(Event(self.name + '/' + name, *args, **kw))

    def emit_status(self, status, old, why):
        ''' Status update callback '''
        self.emit_raw(Event('status', status, old, why))

    def emit_raw(self, event):
        return self.sendServer(event, lambda ev: self.protocol.emit_raw(ev))

    def request(self, name, *args, **kw):
        return self.request_raw(Event(name, *args, **kw))

    def request_raw(self, event):
        return self.sendServer(event, lambda ev: self.protocol.request_raw(ev))


    def sendServer(self, event, protofn):
        ''' Send a message to the protocol. If the node is not connected queue
            the message.
        '''

        if self.protocol:
            # If the protocol is avaible, simply call the function
            # It will return a deferred for us.
            return protofn(event)

        # Create a defer object for the future reply
        defer = Deferred()
        self.queue.put((defer, protofn, event))

        self.log.info("{e}  --  Not connected to server, "
                      "queueing. {n} items in queue",
                      e=event, n=self.queue.qsize())

        return defer


    def sendQueue(self):
        ''' (Attempt to) send the accumulated queue to the protocol. '''

        if not self.protocol:
            return

        self.log.info("Flushing queue of {n} items...", n=self.queue.qsize())

        try:
            while True:
                (defer, protofn, event) = self.queue.get(False)
                self.log.info("Sending {e}", e=event)
                result = protofn(event)
                if isinstance(result, Deferred):
                    result.chainDeferred(defer)
                else:
                    defer.callback(result)
        except Empty:
            pass

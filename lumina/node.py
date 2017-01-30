#-*- python -*-
from __future__ import absolute_import

import os
from binascii import hexlify

from twisted.internet import reactor
from twisted.internet.defer import maybeDeferred
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols.basic import LineReceiver
from twisted.internet.task import LoopingCall

from lumina.plugin import Plugin
from lumina.event import Event
from lumina.exceptions import NoConnectionException, UnknownCommandException
from lumina.log import Logger
from lumina.state import ColorState



# Exception types that will not result in a local traceback
validNodeExceptions = (
    NoConnectionException,
)


class NodeProtocol(LineReceiver):
    noisy = False
    delimiter = '\n'


    def __init__(self, parent):
        self.parent = parent
        self.log = parent.log


    def connectionMade(self):
        self.ip = "%s:%s" %(self.transport.getPeer().host, self.transport.getPeer().port)
        self.parent.protocol = self
        self.log.info("Connected to {ip}", ip=self.ip)

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
        self.parent.emit_next()


    def connectionLost(self, reason):
        self.log.info("Lost connection with {ip}", ip=self.ip)
        self.parent.protocol = None
        self.keepalive.stop()


    def lineReceived(self, data):
        ''' Handle messages from the controller, which are commands that shall
            be executed '''

        # Empty lines are simply ignored
        if not len(data):
            return

        self.log.debug('', rawin=data)

        # -- Parse the incoming message
        try:
            event = Event().load_json(data)
            #event.system = self.system
            self.log.debug('', cmdin=event)

        except (SyntaxError, ValueError) as e:
            # Raised if the load_json didn't succeed
            self.log.error("Protocol error on incoming message: {e}", e.message)
            return

        # -- Handle 'exit' event
        if event.name == 'exit':
            self.transport.loseConnection()
            return

        # -- Handle commands from controller
        else:

            # Call the command function and setup proper response handlers.
            defer = self.parent.run_command(event)
            defer.addBoth(lambda r, c: self.send(c, response=r), event)

            # FIXME: Do we need the defer object for anything else?

            # FIXME: Should the call be encased in a try-except block?

            return


    def emit(self, name, *args, **kw):
        self.send(Event(name, *args, **kw))


    def send(self, event, response=None):
        # The response argument is for passing the deferred responsen when
        # this function is used in a callback/errback chain.

        # Logging
        self.log.debug('', cmdout=event)

        # Encoding and transmittal
        data = event.dump_json()
        self.log.debug('', rawout=data)
        self.transport.write(data+'\n')

        return response


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
        'port'  : dict(default=5326, help='Controller server port', type=int),
        'server': dict(default='localhost', help='Controller to connect to'),
    }


    def setup(self, main):
        self.log = Logger(namespace=self.name)

        # Subscribe to the change of state by sending status back to server
        self.status = ColorState(log=self.log, callback=self.emit_status)

        self.host = main.config.get('server', name=self.name)
        self.port = main.config.get('port', name=self.name)
        self.hostname = main.hostname
        self.hostid = main.hostid
        self.nodeid = hexlify(os.urandom(4))

        self.protocol = None
        self.queue = []

        self.factory = NodeFactory(parent=self)
        reactor.connectTCP(self.host, self.port, self.factory)


    def emit(self, name, *args, **kw):
        # Emit an event to the server
        # Queue it here rather than in the procol, as the procol object is created
        # when the connection to the controller is made

        # FIXME: Return deferred object here?

        event = Event(name, *args, **kw)
        self.queue.append(event)
        if self.protocol is None:
            self.log.info("{e}  --  Not connected to server, "
                          "queueing. {n} items in queue",
                          e=event, n=len(self.queue))

        # Attempt sending the message
        self.emit_next()


    def emit_next(self):
        ''' Send the next event(s) in the queue '''

        if self.protocol is None:
            return
        while len(self.queue):
            event = self.queue.pop(0)
            self.protocol.send(event)


    def emit_status(self, status, old, why):
        self.emit('status', status, old, why)


    def run_command(self, event, unknown_command=True):
        ''' Run a command and return a deferred object for the reply '''

        def _unknown_command(event):
            raise UnknownCommandException(event.name)

        # FIXME: Add proper unknown_command logic
        d = maybeDeferred(self.commands.get(event.name, _unknown_command), event)

        # FIXME: Add config setting to enable/disable logcmdok/logcmderr

        # FIXME: Implement a timeout mechanism here?

        # -- Setup filling in the event data from the result
        def cmd_ok(result, event):
            event.set_success(result)
            self.log.info('', cmdok=event)
            return result

        def cmd_error(failure, event):
            event.set_fail(failure)
            self.log.info('', cmderr=event)

            # FIXME: What failures should be excepted and not passed on?
            #        if not failure.check(CommandException):
            #        log(failure.getTraceback(), system=self.system)

            # Accept the exception if listed in validNodeExceptions.
            for exc in validNodeExceptions:
                if failure.check(exc):
                    return None

            # If failure is returned, it will create a "unhandled exception" and a traceback in
            # the logs. Hence a log() traceback is only necessary when the exception is handled,
            # but one wants traceback.
            return failure

        d.addCallback(cmd_ok, event)
        d.addErrback(cmd_error, event)
        return d

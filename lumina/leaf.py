#-*- python -*-
from __future__ import absolute_import

from twisted.internet import reactor
from twisted.internet.defer import Deferred,maybeDeferred
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols.basic import LineReceiver
from twisted.internet.task import LoopingCall

from .plugin import Plugin
from .event import Event
from .exceptions import *
from .log import *



class LeafProtocol(LineReceiver):
    noisy = False
    delimiter='\n'


    def __init__(self, parent):
        self.parent = parent
        self.system = parent.system


    def connectionMade(self):
        self.ip = "%s:%s" %(self.transport.getPeer().host,self.transport.getPeer().port)
        self.parent.protocol = self
        log("Connected to %s" %(self.ip,), system=self.system)

        # -- Keepalive pings
        self.keepalive = LoopingCall(self.transport.write, '\n')
        self.keepalive.start(60, False)

        # -- Register leaf name
        log("Registering client %s" %(self.parent.name,), system=self.system)
        self.send(Event('name',self.parent.name))

        # -- Send host name
        log("Registering hostname %s" %(self.parent.hostname,), system=self.system)
        self.send(Event('hostname',self.parent.hostname))

        # -- Register events
        evlist = self.parent.events
        if len(evlist):
            log("Registering %s client events" %(len(evlist)), system=self.system)
            self.send(Event('events', *evlist))

        # -- Register commands
        cmdlist = self.parent.commands.keys()
        if len(cmdlist):
            log("Registering %s client commands" %(len(cmdlist)), system=self.system)
            self.send(Event('commands', *cmdlist))

        # -- Flush any queue that might have been accumulated before
        #    connecting to the controller
        self.parent._send()


    def connectionLost(self, reason):
        log("Lost connection with %s" %(self.ip), system=self.system)
        self.parent.protocol = None
        self.keepalive.stop()


    def lineReceived(self, data):
        ''' Handle messages from the controller, which are commands that shall
            be executed '''

        # Empty lines are simply ignored
        if not len(data):
            return

        lograwin(data, system=self.system)

        # -- Parse the incoming message
        try:
            event = Event().load_json(data)
            event.system = self.system
            logdatain(event, system=self.system)

        except (SyntaxError,ValueError) as e:
            # Raised if the load_json didn't succeed
            err("Protocol error on incoming message: %s" %(e.message), system=self.system)
            return

        # -- Handle 'exit' event
        if event.name == 'exit':
            self.transport.loseConnection()
            return

        # -- Handle commands from controller
        else:

            # Call the command function and setup proper response handlers.
            defer = self.parent.run_command(event)
            defer.addBoth(lambda r,c: self.send(c,response=r),event)

            # FIXME: Do we need the defer object for anything else?

            # FIXME: Should the call be encased in a try-except block?

            return


    def send(self, event, response=None):
        # The response argument is for passing the deferred responsen when
        # this function is used in a callback/errback chain.

        # Logging
        logdataout(event, system=self.system)

        # Encoding and transmittal
        data=event.dump_json()
        lograwout(data, system=self.system)
        self.transport.write(data+'\n')

        return response


class LeafFactory(ReconnectingClientFactory):
    noisy = False
    maxDelay = 10
    factor=1.6180339887498948

    def __init__(self,parent):
        self.parent = parent
        self.system = parent.system

    def buildProtocol(self, addr):
        self.resetDelay()
        return LeafProtocol(parent=self.parent)

    def clientConnectionLost(self, connector, reason):
        log(reason.getErrorMessage(), system=self.system)
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        log(reason.getErrorMessage(), system=self.system)
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)



class Leaf(Plugin):
    ''' Leaf objects for plugins '''

    events = { }
    commands = { }

    # Endpoint configuration options
    CONFIG = {
        'port'  : dict(default=8081, help='Controller server port', type=int ),
        'server': dict(default='localhost', help='Controller to connect to' ),
    }


    def setup(self, main):
        self.hostname = 'foobar'
        self.host = main.config.get('server',name=self.name)
        self.port = main.config.get('port',name=self.name)
        self.system = self.name
        self.protocol = None
        self.queue = []
        self.factory = LeafFactory(parent=self)
        reactor.connectTCP(self.host, self.port, self.factory)


    def event(self, event, *args, **kw):
        self.send(Event(event,*args,**kw))


    def send(self, event):
        # Queue it here rather than in the procol, as the procol object is created
        # when the connection to the controller is made
        self.queue.append(event)
        if self.protocol is None:
            log("%s  --  Not connected to server, queueing" %(event), system=self.system)

        # Attempt sending the message
        self._send()


    def _send(self):
        ''' Send the next event(s) in the queue '''

        if self.protocol is None:
            return None
        while(len(self.queue)):
            event = self.queue.pop(0)
            self.protocol.send(event)


    def run_command(self, event, unknown_command=True):
        ''' Run a command and return a deferred object for the reply '''

        def _unknown_command(event):
            raise UnknownCommandException(event.name)

        # FIXME: Add proper unknown_command logic
        d = maybeDeferred(self.commands.get(event.name, _unknown_command), event)

        # FIXME: Add config setting for logcmdok/logcmderr

        # -- Setup filling in the event data from the result
        def cmd_ok(result,event):
            event.success = True
            if isinstance(result,Event):
                event.result = result.result
            else:
                event.result = result
            logcmdok(event, system=self.system)
            return result

        def cmd_error(failure,event):
            # Build an error response containing a tuple of
            # (exception class name,failure text)
            cls = failure.value.__class__.__name__
            text = str(failure.value)
            event.success = False
            event.result = (cls,text)
            logcmderr(event, system=self.system)

            # FIXME: What failures should be excepted and not passed on?
            #        if not failure.check(CommandException):
            #        log(failure.getTraceback(), system=self.system)

            # If failure is returned, it will create a "unhandled exception" and a traceback in
            # the logs. Hence a log() traceback is only necessary when the exception is handled,
            # but one wants traceback.
            return failure

        d.addCallback(cmd_ok,event)
        d.addErrback(cmd_error,event)
        return d

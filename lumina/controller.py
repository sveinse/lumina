# -*- python -*-
import os,sys
from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet.defer import Deferred,maybeDeferred

from core import Core
from event import Event
from exceptions import *
from log import *


validClientExceptions = (
    CommandFailedException,
)


class EventProtocol(LineReceiver):
    noisy = False
    delimiter='\n'
    timeout=15
    system = 'CTRL'
    seq = 0

    def connectionMade(self):
        self.ip = "%s:%s" %(self.transport.getPeer().host,self.transport.getPeer().port)
        self.name = self.ip
        self.events = []
        self.commands = []
        self.requests = { }
        log("Connect from %s" %(self.ip,), system=self.system)


    def connectionLost(self, reason):
        log("Lost connection from '%s' (%s)" %(self.name,self.ip), system=self.system)
        if len(self.events):
            log("%s de-registering %s events" %(self.name, len(self.events)),
                system=self.system)
            self.parent.remove_events(self.events)
        if len(self.commands):
            log("%s de-registering %s commands" %(self.name, len(self.commands)),
                system=self.system)
            self.parent.remove_commands(self.commands)
        # FIXME: Cancel all pending request?


    def lineReceived(self, data):
        ''' Handle messages from the clients '''

        # -- Empty lines are simply ignored
        if not len(data):
            return

        lograwin(data, system=self.system)

        # -- Special @ notation which makes the controller execute the incoming data as a command
        if data.startswith('@'):
            self.interactive(data)
            return

        # -- Parse the incoming message as an Event
        try:
            event = Event().parse_json(data)
            #logdatain(event, system=self.name)

        except (SyntaxError,ValueError) as e:
            # Raised if the parse_json didn't succeed
            err(system=self.system)
            log("Protcol error on incoming message: %s" %(e.message), system=self.system)
            return

        # -- Register client name
        if event.name == 'name':
            self.name = 'R-' + event.args[0]
            log("***  Registering client %s (%s)" %(self.name,self.ip), system=self.system)
            return

        # -- Register client events
        elif event.name == 'events':
            evlist = event.args[:]
            if len(evlist):
                log("%s registering %s events" %(self.name,len(evlist)),
                    system=self.system)
                self.events = evlist
                self.parent.add_events(evlist)
            return

        # -- Register client commands
        elif event.name == 'commands':
            evlist = event.args[:]
            if len(evlist):
                log("%s registering %s commands" %(self.name,len(evlist)),
                    system=self.system)
                self.commands = evlist
                # Register the received list of commands and point them
                # to this instance's send function. This will simply send
                # the message to the client.
                commands = {}
                for a in evlist:
                    commands[a] = lambda a : self.send(a)
                self.parent.add_commands(commands)
            return

        # -- Handle 'exit' event
        elif event.name == 'exit':
            self.transport.loseConnection()
            return

        # -- Handle error to a former command
        elif event.name == 'error':
            self.error(event)
            return

        # -- Handle a reply to a former command
        elif 'seq' in event.kw:
            self.response(event)
            return

        # -- A new incoming (async) event.
        else:
            self.parent.handle_event(event)


    # -- Send a command to the client
    def send(self, event):
        self.seq += 1
        event.defer = Deferred()
        event.timer = reactor.callLater(self.timeout, self.timedout, event)
        event.kw['seq'] = self.seq
        self.requests[self.seq] = event

        #logdataout(event, system=self.name)

        data=event.dump_json()+'\n'
        lograwout(data, system=self.system)
        self.transport.write(data)
        return event.defer


    # -- TIMEOUT response handler
    def timedout(self, event):
        logtimeout(event, system=self.name)
        request = self.requests.pop(event.kw['seq'])

        request.defer.errback(TimeoutException())


    # -- OK response handler
    def response(self, event):
        request = self.requests.pop(event.kw['seq'])

        # FIXME: Perhaps the payload should be a separate object(type), not the event itself?
        request.timer.cancel()
        request.defer.callback(event)


    # -- ERROR response handler
    def error(self, event):

        failure = event.args[0]
        request = self.requests.pop(failure)

        # Parse exception types
        ename = event.args[1]
        eargs = event.args[2:]
        el = [ e.__name__ for e in validClientExceptions ]
        if ename in el:
            ei = el.index(ename)
            exc = validClientExceptions[ei](eargs)
        else:
            exc = ClientException(eargs)

        request.timer.cancel()
        request.defer.errback(exc)


    # -- @INTERACTIVE mode (lines prefixed with '@')
    def interactive(self, data):

        def raw_reply(reply,cls,event):
            cls.transport.write(">>> %s\n" %(str(reply),))
        def raw_error(reply,cls,event):
            cls.transport.write(">>> %s FAILED: %s %s\n" %(
                event,reply.value.__class__.__name__,str(reply.value)))
            raise reply

        try:
            event = Event().parse_str(data)
            logdatain(event, system=self.name)
        except SyntaxError as e:
            err(system=self.system)
            log("Protcol error: %s" %(e.message), system=self.system)
            self.transport.write('>>> ERROR: Protocol error. %s\n' %(e.message))
            return

        event.name = event.name[1:]
        try:
            result = self.parent.run_command(event)
            result.addCallback(raw_reply, self, event)
            result.addErrback(raw_error, self, event)
        except CommandError as e:
            err(system=self.system)
            self.transport.write('>>> %s ERROR: %s\n' %(event,e.message))



class EventFactory(Factory):
    noisy = False

    def buildProtocol(self, addr):
        proto = EventProtocol()
        proto.parent = self.parent
        return proto



class Controller(Core):
    system = 'CTRL'

    def __init__(self,port):
        Core.__init__(self)
        self.port = port


    def setup(self):
        self.factory = EventFactory()
        self.factory.parent = self
        reactor.listenTCP(self.port, self.factory)


    def handle_event(self, event):
        ''' Event dispatcher. Event contains messages coming from the device endpoints. '''

        logevent(event, system='EVENT')

        # Is this a registered event?
        if event.name not in self.events:
            log("     --:  Unknown event, ignoring", system='EVENT')
            return None

        # Run the job
        self.run_job(event)

# -*- python -*-
import os,sys
import traceback
from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from twisted.internet.defer import Deferred,maybeDeferred

from core import Core
from event import Event
from exceptions import *


validClientExceptions = (
    CommandFailedException,
)


class EventProtocol(LineReceiver):
    noisy = False
    delimiter='\n'
    timeout=15
    system = 'CTRL'

    def connectionMade(self):
        self.ip = "%s:%s" %(self.transport.getPeer().host,self.transport.getPeer().port)
        self.name = self.ip
        self.events = []
        self.commands = []
        self.requests = { }
        log.msg("Connect from %s" %(self.ip,), system=self.system)


    def connectionLost(self, reason):
        log.msg("Lost connection from '%s' (%s)" %(self.name,self.ip), system=self.system)
        if len(self.events):
            self.parent.remove_events(self.events)
        if len(self.commands):
            self.parent.remove_commands(self.commands)
        # FIXME: Cancel all pending request?


    def lineReceived(self, data):
        ''' Handle messages from the clients '''

        # -- Empty lines are simply ignored
        if not len(data):
            return

        # -- Special @ notation which makes the controller execute the incoming data as a command
        if data.startswith('@'):
            self.interactive(data)
            return

        # -- Parse the incoming message as an Event
        try:
            event = Event().parse_json(data)
            evm = event.copy()
            if event.name in ('events', 'commands'):
                evm.args=['...%s args...' %(len(event.args))]
            log.msg("   -->  %s" %(evm,), system=self.name)
        except SyntaxError as e:
            log.msg("Protcol error. %s" %(e.message), system=self.system)
            return

        # -- Register client name
        if event.name == 'name':
            self.name = 'R-' + event.args[0]
            log.msg("Client %s identified as '%s'" %(self.ip,self.name), system=self.system)
            return

        # -- Register client events
        elif event.name == 'events':
            evlist = event.args[:]
            if len(evlist):
                self.events = evlist
                self.parent.add_events(evlist)
            return

        # -- Register client commands
        elif event.name == 'commands':
            evlist = event.args[:]
            if len(evlist):
                self.commands = evlist
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
        elif event.name in self.requests:
            self.response(event)
            return

        # -- A new incoming (async) event.
        else:
            self.parent.handle_event(event)


    # -- Send a command to the client
    def send(self, event):
        d = Deferred()
        self.requests[event.name] = {
            'defer': d,
            'timer': reactor.callLater(self.timeout, self.timedout, event),
        }
        log.msg("   <--  %s" %(event,), system=self.name)
        self.transport.write(event.dump_json()+'\n')
        return d


    # -- TIMEOUT response handler
    def timedout(self, event):
        log.msg('   -->  TIMEOUT %s' %(event,), system=self.name)
        request = self.requests[event.name]
        d = request['defer']
        del self.requests[event.name]

        d.errback(TimeoutException())


    # -- OK response handler
    def response(self, event):
        request = self.requests[event.name]
        d = request['defer']
        request['timer'].cancel()
        del self.requests[event.name]

        # FIXME: Perhaps the payload should be a separate object(type), not the event itself?
        d.callback(event)


    # -- ERROR response handler
    def error(self, event):

        failure = event.args[0]
        request = self.requests[failure]
        request['timer'].cancel()
        d = request['defer']
        del self.requests[failure]

        # Parse exception types
        ename = event.args[1]
        eargs = event.args[2:]
        el = [ e.__name__ for e in validClientExceptions ]
        if ename in el:
            ei = el.index(ename)
            exc = validClientExceptions[ei](eargs)
        else:
            exc = ClientException(eargs)

        d.errback(exc)


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
            log.msg("   -->  %s" %(event,), system=self.name)
        except SyntaxError as e:
            log.msg("Protcol error. %s" %(e.message), system=self.system)
            self.transport.write('>>> ERROR: Protocol error. %s\n' %(e.message))
            return

        cmdevent = Event(event.name[1:],*event.args,**event.kw)
        fn = self.parent.get_commandfn(cmdevent.name)
        if not fn:
            self.transport.write('>>> %s ERROR: Event not found.\n' %(cmdevent,))
            return

        self.transport.write("<<< %s\n" %(cmdevent,))
        result = maybeDeferred(fn, cmdevent)
        result.addCallback(raw_reply, self, cmdevent)
        result.addErrback(raw_error, self, cmdevent)



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

        # Is this a registered event?
        if event.name not in self.events:
            log.msg("%s  --  Unregistered" %(event), system=self.system)
            return None

        # Known event?
        if event.name not in self.jobs:
            log.msg("%s  --  Ignored, no job handler" %(event), system=self.system)
            #log.msg("   No job for event '%s', ignoring" %(event.name), system=self.system)
            return None

        log.msg("%s" %(event), system=self.system)

        # Get the job and run it
        job = self.jobs[event.name]
        job.event = event
        self.run_job(job)

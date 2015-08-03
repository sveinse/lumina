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
    CommandException,
)


class EventProtocol(LineReceiver):
    noisy = False
    delimiter='\n'
    timeout=15
    system = 'CTRL'

    def connectionMade(self):
        self.ip = "%s:%s" %(self.transport.getPeer().host,self.transport.getPeer().port)
        self.name = self.system + ':' + self.ip
        self.events = []
        self.commands = []
        self.requests = { }
        log("Connect from %s" %(self.ip,), system=self.system)


    def connectionLost(self, reason):
        log("Lost connection from '%s' (%s)" %(self.name,self.ip), system=self.system)
        if len(self.events):
            log("De-registering %s events" %(len(self.events)), system=self.name)
            self.parent.remove_events(self.events)
        if len(self.commands):
            log("De-registering %s commands" %(len(self.commands)), system=self.name)
            self.parent.remove_commands(self.commands)
        # FIXME: Cancel all pending request?


    def lineReceived(self, data):
        ''' Handle messages from the clients '''

        # -- Empty lines are simply ignored
        if not len(data):
            return

        lograwin(data, system=self.name)

        # -- Special @ notation which makes the controller execute the incoming data as a command
        if data.startswith('@'):
            self.interactive(data)
            return

        # -- Parse the incoming message as an Event
        try:
            event = Event().load_json(data)
            logdatain(event, system=self.name)

        except (SyntaxError,ValueError) as e:
            # Raised if the load_json didn't succeed
            err(system=self.name)
            log("Protcol error on incoming message: %s" %(e.message), system=self.name)
            return

        # -- Register client name
        if event.name == 'name':
            self.name = self.system + ':' + event.args[0]
            log("***  Registering client %s (%s)" %(event.args[0],self.ip), system=self.name)
            return

        # -- Register client events
        elif event.name == 'events':
            evlist = event.args[:]
            if len(evlist):
                log("Registering %s events" %(len(evlist)), system=self.name)
                self.events = evlist
                self.parent.add_events(evlist)
            return

        # -- Register client commands
        elif event.name == 'commands':
            evlist = event.args[:]
            if len(evlist):
                log("Registering %s commands" %(len(evlist)), system=self.name)
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

        # -- Handle a reply to a former command
        elif event.id in self.requests:
            if event.success:
                self.response(event)
            else:
                self.error(event)
            return

        # -- A new incoming (async) event.
        else:
            self.parent.handle_event(event)


    # -- Send a command to the client
    def send(self, event):
        #self.seq += 1
        event.defer = Deferred()
        event.gen_id()
        #event.timer = reactor.callLater(self.timeout, self.timedout, event)
        #event.kw['seq'] = self.seq
        self.requests[event.id] = event

        logdataout(event, system=self.name)

        data=event.dump_json()
        lograwout(data, system=self.name)
        self.transport.write(data+'\n')
        return event.defer


    # -- TIMEOUT response handler
    #def timedout(self, event):
    #    logtimeout(event, system=self.name)
    #    request = self.requests.pop(event.id)

    #    request.defer.errback(TimeoutException())


    # -- OK response handler
    def response(self, event):
        #log("RESP",event)
        request = self.requests.pop(event.id)
        request.del_id()

        # FIXME: Perhaps the payload should be a separate object(type), not the event itself?
        #request.timer.cancel()
        request.defer.callback(event.result)


    # -- ERROR response handler
    def error(self, event):

        result = event.result
        request = self.requests.pop(event.id)
        request.del_id()

        # Parse exception types
        ename = result[0]
        eargs = result[1:]
        el = [ e.__name__ for e in validClientExceptions ]
        if ename in el:
            ei = el.index(ename)
            exc = validClientExceptions[ei](*eargs)
        else:
            # Unknow exceptions are mapped to this type
            eargs.insert(0,ename)
            exc = ClientException(*eargs)

        #request.timer.cancel()
        request.defer.errback(exc)


    # -- @INTERACTIVE mode (lines prefixed with '@')
    def interactive(self, data):

        def raw_reply(reply,cls,event):
            if not isinstance(reply.success,bool):
                (result,reply.result)=(reply.result,'(...)')
                for r in result:
                    cls.transport.write("     %s\n" %(str(r),))
            cls.transport.write(">>>  %s\n" %(str(reply),))
        def raw_error(failure,cls,event):
            cls.transport.write(">>>  %s FAILED: %s %s\n" %(
                event.name,failure.value.__class__.__name__,str(failure.value)))

        try:
            event = Event().load_str(data)
            event.system = self.system
            logdatain(event, system=self.name)
        except SyntaxError as e:
            err(system=self.system)
            log("Protcol error: %s" %(e.message), system=self.name)
            self.transport.write('>>>  ERROR: Protocol error. %s\n' %(e.message))
            return

        event.name = event.name[1:]
        try:
            cmdlist = self.parent.get_commandfnlist(event)
            self.transport.write('<<<  %s\n' %(cmdlist))
            defer = self.parent.run_commandlist(event, cmdlist)
            defer.addCallback(raw_reply, self, event)
            defer.addErrback(raw_error, self, event)
        except CommandException as e:
            # Handles any errors before the commands are run
            err(system=self.system)
            self.transport.write('>>>  %s ERROR: %s\n' %(event,e.message))



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

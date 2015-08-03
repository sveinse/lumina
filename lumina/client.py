# -*- python -*-
import os,sys

import twisted.internet.protocol as protocol
from twisted.internet import reactor
from twisted.internet.defer import Deferred,maybeDeferred
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols.basic import LineReceiver
from twisted.internet.task import LoopingCall

from core import Core
from event import Event
from exceptions import *
from log import *


class EventProtocol(LineReceiver):
    noisy = False
    delimiter='\n'
    system = 'CLIENT'


    def connectionMade(self):
        self.ip = "%s:%s" %(self.transport.getPeer().host,self.transport.getPeer().port)
        self.parent.protocol = self
        log("Connected to %s" %(self.ip,), system=self.system)

        # -- Keepalive pings
        self.loop = LoopingCall(self.keepalive)
        self.loop.start(60, False)

        # -- Register name
        log("Registering client %s" %(self.parent.name,), system=self.system)
        self.send_event(Event('name',self.parent.name))

        # -- Register events
        evlist = self.parent.events
        if len(evlist):
            #log("Registering %s client events" %(len(evlist)), system=self.system)
            self.send_event(Event('events', *evlist))

        # -- Register commands
        cmdlist = self.parent.commands.keys()
        if len(cmdlist):
            #log("Registering %s client commands" %(len(cmdlist)), system=self.system)
            self.send_event(Event('commands', *cmdlist))

        # -- Flush any queue that might have been accumulated before
        #    connecting to the controller
        self.parent.send_events()


    def connectionLost(self, reason):
        log("Lost connection with %s" %(self.ip), system=self.system)
        self.parent.protocol = None
        self.loop.stop()


    def lineReceived(self, data):
        ''' Handle messages from the controller, which are commands that shall
            be executed '''

        # Empty lines are simply ignored
        if not len(data):
            return

        lograwin(data, system=self.system)

        # -- Parse the incoming message
        try:
            request = Event().parse_json(data)
            logdatain(request, system=self.system)

        except (SyntaxError,ValueError) as e:
            # Raised if the parse_json didn't succeed
            err(system=self.system)
            log("Protocol error on incoming message: %s" %(e.message), system=self.system)
            return

        # -- Handle 'exit' event
        if request.name == 'exit':
            self.transport.loseConnection()
            return

        # -- Handle commands from controller
        else:
            try:

                # Call the command function and setup proper response handlers.
                request.system = self.system
                cmdlist = self.parent.get_commandfnlist(request)
                defer = self.parent.run_commandlist(request, cmdlist)
                #defer = self.parent.run_command(request)
                defer.addCallback(self.send_reply, request)
                defer.addErrback(self.send_error, request)

            except CommandError as e:
                # Raised if composing the commands fails
                err(system=self.system)
                log("Error in command '%s'. %s" %(request.name,e.message),system=self.system)
            return


    def keepalive(self):
        self.transport.write('\n')


    def send_event(self, event):

        # Logging
        logdataout(event, system=self.system)

        # Encoding and transmittal
        data=event.dump_json()+'\n'
        lograwout(data, system=self.system)
        self.transport.write(data)


    def send_reply(self, response, request):
        log("REPLY to %s: %s" %(request.name, response), system=self.system)

        # FIXME: Check what object being returned to controller with new setup

        # Wrap common reply type into Event object that can be transferred
        # to the server.
        #if response is None:
        #    response = Event(request.name)
        ##elif isinstance(response, Event):
        ##    response.name = request.name
        #elif type(response) is list or type(response) is tuple:
        #    response = Event(request.name,*response)
        #else:
        #    response = Event(request.name,response)

        # Copy the sequence number from the request
        #response.kw['seq'] = request.kw['seq']

        self.send_event(response)


    def send_error(self, failure, request):
        failtype = failure.trap(CommandException)
        reason = failure.value

        # Wrap in error Event object to be able to send back to the controller
        # error syntax {event_name, exception_name, exception args}
        error = Event('error',request.name,reason.__class__.__name__,*reason.args)
        self.send_event(error)



class EventFactory(ReconnectingClientFactory):
    noisy = False
    maxDelay=10
    factor=1.6180339887498948
    system = 'CLIENT'

    def buildProtocol(self, addr):
        self.resetDelay()
        proto = EventProtocol()
        proto.parent = self.parent
        proto.system = self.parent.system
        return proto

    def clientConnectionLost(self, connector, reason):
        log(reason.getErrorMessage(), system=self.system)
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        log(reason.getErrorMessage(), system=self.system)
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)



class Client(Core):
    system = 'CLIENT'


    def __init__(self,host,port,name):
        Core.__init__(self)
        self.host = host
        self.port = port
        self.name = name
        self.protocol = None
        self.queue = []
        self.system = name


    def setup(self):
        self.factory = EventFactory()
        self.factory.parent = self
        self.factory.system = self.system
        reactor.connectTCP(self.host, self.port, self.factory)


    def handle_event(self, event):
        ''' Event dispatcher. Events contains messages coming from the device
            endpoints and should be forwarded to the controller over the network '''

        # Queue it here rather than in the procol, as the procol object is created
        # when the connection to the controller is made
        self.queue.append(event)
        if self.protocol is None:
            log("%s  --  Not connected to server, queueing" %(event), system=self.system)

        # Attempt sending the message
        self.send_events()


    def send_events(self):
        ''' Send the next event(s) in the queue '''

        if self.protocol is None:
            return None
        while(len(self.queue)):
            event = self.queue.pop(0)
            self.protocol.send_event(event)

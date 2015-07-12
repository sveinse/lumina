import os,sys
import traceback

import twisted.internet.protocol as protocol
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from twisted.internet.task import LoopingCall

from core import Event,Core



class EventProtocol(LineReceiver):
    noisy = False
    delimiter='\n'

    def connectionMade(self):
        self.ip = "%s:%s" %(self.transport.getPeer().host,self.transport.getPeer().port)
        self.parent.protocol = self
        log.msg("Connected to %s" %(self.ip,), system='CLIENT')

        # -- Keepalive pings
        self.loop = LoopingCall(self.keepalive)
        self.loop.start(60, False)

        # -- Register name
        log.msg("Registering name '%s'" %(self.parent.name,), system='CLIENT')
        self.send_event(Event('name',self.parent.name))

        # -- Register events
        evlist = self.parent.events
        if len(evlist):
            log.msg("Registering events %s" %(evlist), system='CLIENT')
            self.send_event(Event('events', *evlist))

        # -- Register actions
        evlist = self.parent.actions.keys()
        if len(evlist):
            log.msg("Registering actions %s" %(evlist), system='CLIENT')
            self.send_event(Event('actions', *evlist))

        # -- Flush any queue that might have been accumulated before
        #    connecting to the controller
        self.parent.send_events()


    def connectionLost(self, reason):
        log.msg("Lost connection with %s" %(self.ip), system='CLIENT')
        self.parent.protocol = None
        self.loop.stop()


    def lineReceived(self, data):
        ''' Handle messages from the controller, which are actions that shall
            be executed '''

        # Empty lines are simply ignored
        if not len(data):
            return

        try:
            event = Event().parse(data)
            log.msg("   -->  %s" %(event,), system='CLIENT')
        except SyntaxError as e:
            log.msg("Protocol error. %s" %(e.message))
            return

        # -- Handle 'exit' event
        if event.name == 'exit':
            self.transport.loseConnection()
            return

        # -- Handle events from controller (actions)
        else:
            # Get the the action function
            fn = self.parent.get_actionfn(event.name)
            if not fn:
                return

            # Call the action function. If a Deferred object is returned, we set to
            # call this function when the results from the operation is ready
            try:
                result = fn(event)
                if isinstance(result, Deferred):
                    result.addCallback(self.send_reply, event)
                    result.addErrback(self.send_error, event)
                    return
                else:
                    self.send_reply(result, event)
                    return
            except Exception as e:
		traceback.print_exc()
                self.send_error(e, event)


    def keepalive(self):
        self.transport.write('\n')


    def send_event(self, event):
        # No response is expected from events, so no need to setup any deferals
        log.msg("   <--  %s" %(event,), system='CLIENT')
        self.transport.write(event.dump()+'\n')


    def send_reply(self, reply, request):
        log.msg("REPLY to %s: %s" %(request.name, reply))

        # Wrap common reply type into Event object that can be transferred
        # to the server.
        if reply is None:
            reply = Event(request.name)
        #elif isinstance(reply, Event):
        #    reply.name = request.name
        elif type(reply) is list or type(reply) is tuple:
            reply = Event(request.name,*reply)
        else:
            reply = Event(request.name,reply)

        log.msg("   <--  %s" %(reply,), system='CLIENT')
        self.transport.write(reply.dump()+'\n')


    def send_error(self, reply, request):
        log.msg("FAIL on %s: %s" %(request.name, reply))

        # FIXME: Wrap local exceptions into event massages that can be transferred
        #        over the net
        error = Event('error',request.name,str(reply))

        log.msg("   <--  %s" %(error,), system='CLIENT')
        self.transport.write(error.dump()+'\n')



class EventFactory(ReconnectingClientFactory):
    noisy = False
    maxDelay=10
    factor=1.6180339887498948

    def buildProtocol(self, addr):
        self.resetDelay()
        proto = EventProtocol()
        proto.parent = self.parent
        return proto

    def clientConnectionLost(self, connector, reason):
        log.msg(reason.getErrorMessage(), system='CLIENT')
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        log.msg(reason.getErrorMessage(), system='CLIENT')
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)



class Client(Core):

    def __init__(self,host,port,name):
        Core.__init__(self)
        self.host = host
        self.port = port
        self.name = name
        self.protocol = None
        self.queue = []


    def setup(self):
        self.factory = EventFactory()
        self.factory.parent = self
        reactor.connectTCP(self.host, self.port, self.factory)


    def handle_event(self, event):
        ''' Event dispatcher. Events contains messages coming from the device
            endpoints and should be forwarded to the controller over the network '''

        # Queue it here rather than in the procol, as the procol object is created
        # when the connection to the controller is made
        self.queue.append(event)
        if self.protocol is None:
            log.msg("%s  --  Not connected to server, queueing" %(event), system='CLIENT')

        # Attempt sending the message
        self.send_events()


    def send_events(self):
        ''' Send the next event(s) in the queue '''

        if self.protocol is None:
            return None
        while(len(self.queue)):
            event = self.queue.pop(0)
            self.protocol.send_event(event)

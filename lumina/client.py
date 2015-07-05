import os,sys

import twisted.internet.protocol as protocol

from twisted.internet import reactor
#from twisted.internet import task
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from twisted.internet.task import LoopingCall

from core import Event,JobBase,Job,Action



class ClientProtocol(LineReceiver):
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
        log.msg("Registering events %s" %(evlist), system='CLIENT')
        self.send_event(Event('events', *evlist))

        # -- Register actions
        evlist = self.parent.actions.keys()
        log.msg("Registering actions %s" %(evlist), system='CLIENT')
        self.send_event(Event('actions', *evlist))

        # -- Flush any queue
        self.parent.flush_queue()


    def connectionLost(self, reason):
        log.msg("Lost connection with %s" %(self.ip), system='CLIENT')
        self.parent.protocol = None
        self.loop.stop()


    def lineReceived(self, data):
        if not len(data):
            return

        request = Action(data, fn=None)
        log.msg("   -->  %s" %(request,), system='CLIENT')

        # -- Handle 'exit' event
        if request.name == 'exit':
            self.transport.loseConnection()

        else:
            result = self.parent.run_action(request)

            # If a Deferred object is returned, we set to call this function when the
            # results from the operation is ready
            if isinstance(result, Deferred):
                result.addCallback(self.send_reply, request)
                result.addErrback(self.send_error, request)
            else:
                self.send_reply(result, request)


    def keepalive(self):
        self.transport.write('\n')


    def send_event(self, event):
        log.msg("   <--  %s" %(event,), system='CLIENT')
        self.transport.write(event.dump()+'\n')


    def send_reply(self, reply, request):
        # Wrap common reply type into Event object that can be transferred
        # to the server.
        if reply is None:
            reply = Event(request.name)
        elif isinstance(reply, Event):
            reply.name = request.name
        elif type(reply) is list:
            reply = Event(request.name,*reply)
        else:
            reply = Event(request.name+'{'+str(reply)+'}')

        log.msg("   <--  %s" %(reply,), system='CLIENT')
        self.transport.write(reply.dump()+'\n')


    def send_error(self, reply, request):
        log.msg("FIXME: %s failed with %s, not implemented" %(request,reply), system='CLIENT')



class ClientFactory(ReconnectingClientFactory):
    noisy = False
    maxDelay=10
    factor=1.6180339887498948

    def startedConnecting(self, connector):
        pass
        #log.msg('Started to connect.')

    def buildProtocol(self, addr):
        self.resetDelay()
        proto = ClientProtocol()
        proto.parent = self.parent
        return proto

    def clientConnectionLost(self, connector, reason):
        log.msg(reason.getErrorMessage(), system='CLIENT')
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        log.msg(reason.getErrorMessage(), system='CLIENT')
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)



class Client(object):

    def __init__(self,host,port,name):
        self.host = host
        self.port = port
        self.name = name

        self.protocol = None

        self.events = []
        self.actions = {}
        self.queue = []


    def setup(self):
        self.factory = ClientFactory()
        self.factory.parent = self
        reactor.connectTCP(self.host, self.port, self.factory)


    def add_events(self, events):
        ''' Add to the list of known events'''

        log.msg("Registering events: %s" %(tuple(events),), system='CLIENT')
        for name in events:
            if name in self.events:
                raise TypeError("Event '%s' already exists" %(name))
            self.events.append(name)


    def add_actions(self, actions):
        ''' Add to the dict of known action and register their callback fns '''

        log.msg("Registering actions: %s" %(tuple(actions.keys()),), system='CLIENT')
        for (name,fn) in actions.items():
            if name in self.actions:
                raise TypeError("Action '%s' already exists" %(name))
            self.actions[name] = fn


    def handle_event(self, event):
        ''' Event dispatcher '''

        #if not event:
        #    return None
        #if not isinstance(event,Event):
        #    event=Event(event)

        #log.msg("%s" %(event), system='CLIENT')

        # Is this a registered event?
        #if event.name not in self.events:
        #    log.msg("%s  --  Unregistered" %(event), system='CLIENT')
        #    return None

        # Known event?
        #if event.name not in self.jobs:
        #    log.msg("%s  --  No job handler" %(event), system='CLIENT')
        #    #log.msg("   No job for event '%s', ignoring" %(event.name), system='CLIENT')
        #    return None

        # Get the job
        #job = self.jobs[event.name]
        #job.event = event
        #return self.run_job(job)

        self.queue.append(event)
        self.flush_queue()


    def flush_queue(self):
        while(len(self.queue)):

            event = self.queue[0]
            if self.protocol is None:
                log.msg("%s  --  Not connected to server, queueing" %(event), system='CLIENT')
                return None

            event = self.queue.pop(0)
            self.protocol.send_event(event)


    def run_action(self, action):

        #action = Action(name=event, fn=None)

        # Known action?
        if action.name not in self.actions:
            log.msg("Unknown action '%s', ignoring" %(action.name), system='CLIENT')
            return None

        # Set the function handler
        action.fn = self.actions[action.name]

        # Execute the action
        return action.execute()

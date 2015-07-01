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


    # Testing
    #def loop_cb():
    #    cli.send('demo/event')

    #loop = LoopingCall(loop_cb)
    #loop.start(1, False)


class ClientProtocol(LineReceiver):
    delimiter='\n'


    def connectionMade(self):
        self.ip = "%s:%s" %(self.transport.getPeer().host,self.transport.getPeer().port)
        self.client.protocol = self
        log.msg("Connected to %s" %(self.ip,), system='CLIENT')

        # -- Keepalive pings
        self.loop = LoopingCall(self.keepalive)
        self.loop.start(60, False)

        # -- Register name
        log.msg("Registering name '%s'" %(self.client.name,), system='CLIENT')
        self.send_event(Event('name',self.client.name))

        # -- Register events
        evlist = self.client.events
        log.msg("Registering events %s" %(evlist), system='CLIENT')
        self.send_event(Event('events', *evlist))

        # -- Register actions
        evlist = self.client.actions.keys()
        log.msg("Registering actions %s" %(evlist), system='CLIENT')
        self.send_event(Event('actions', *evlist))


    def connectionLost(self, reason):
        log.msg("Lost connection with %s" %(self.ip), system='CLIENT')
        self.client.protocol = None
        self.loop.stop()


    def lineReceived(self, data):
        if not len(data):
            return

        request = Action(data, fn=None)
        log.msg("   -->  %s" %(request,), system='CLIENT')
        result = self.client.run_action(request)

        # If a Deferred object is returned, we set to call this function when the
        # results from the operation is ready
        if isinstance(result, Deferred):
            result.addCallback(self.send_reply, request)
        else:
            self.send_reply(result, request)


    def keepalive(self):
        self.transport.write('\n')


    def send_event(self, event):
        log.msg("   <--  %s" %(event,), system='CLIENT')
        self.transport.write(event.dump()+'\n')


    def send_reply(self, reply, request):
        # Parse the incoming data.
        #   None:     Create new empty object using the request name
        #   Event():  Use object, but replace name with request name
        #   *:        Parse via the Event() parser
        if reply is None:
            reply = Event(request.name)
        elif isinstance(reply, Event):
            reply.name = request.name
        else:
            reply = Event(request.name+'{'+reply+'}')
        log.msg("   <--  %s" %(reply,), system='CLIENT')
        self.transport.write(reply.dump()+'\n')



class ClientFactory(ReconnectingClientFactory):
    maxDelay=10
    factor=1.6180339887498948

    def startedConnecting(self, connector):
        pass
        #log.msg('Started to connect.')

    def buildProtocol(self, addr):
        self.resetDelay()
        proto = ClientProtocol()
        proto.client = self.client
        return proto

    #def clientConnectionLost(self, connector, reason):
    #    log.msg('Lost connection.', reason.getErrorMessage())
    #    ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    #def clientConnectionFailed(self, connector, reason):
    #    log.msg('Connection failed.', reason.getErrorMessage())
    #    ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)



class Client(object):

    def __init__(self,host,port,name):
        self.host = host
        self.port = port
        self.name = name

        self.protocol = None

        self.events = []
        self.actions = {}


    def setup(self):
        self.factory = ClientFactory()
        self.factory.client = self
        reactor.connectTCP(self.host, self.port, self.factory)


    def add_events(self, events):
        ''' Add to the list of known events'''

        log.msg("Registering events: %s" %(tuple(events),), system='EVENT')
        for name in events:
            if name in self.events:
                raise TypeError("Event '%s' already exists" %(name))
            self.events.append(name)


    def add_actions(self, actions):
        ''' Add to the dict of known action and register their callback fns '''

        log.msg("Registering actions: %s" %(tuple(actions.keys()),), system='ACTION')
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

        #log.msg("%s" %(event), system='EVENT')

        # Is this a registered event?
        #if event.name not in self.events:
        #    log.msg("%s  --  Unregistered" %(event), system='EVENT')
        #    return None

        if self.protocol is None:
            log.msg("%s  -- Ignoring, not connected to server" %(event), system='EVENT')
            return None

        # Known event?
        #if event.name not in self.jobs:
        #    log.msg("%s  --  No job handler" %(event), system='EVENT')
        #    #log.msg("   No job for event '%s', ignoring" %(event.name), system='EVENT')
        #    return None

        # Get the job
        #job = self.jobs[event.name]
        #job.event = event
        #return self.run_job(job)

        # Send
        self.protocol.send_event(event)


    def run_action(self, action):

        #action = Action(name=event, fn=None)

        # Known action?
        if action.name not in self.actions:
            log.msg("Unknown action '%s', ignoring" %(action.name), system='ACTION')
            return None

        # Set the function handler
        action.fn = self.actions[action.name]

        # Execute the action
        return action.execute()

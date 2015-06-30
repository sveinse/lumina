import os,sys

import twisted.internet.protocol as protocol

from twisted.internet import reactor
#from twisted.internet import task
#from twisted.internet.defer import Deferred
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
        self.chost = self.transport.getPeer().host
        self.cport = self.transport.getPeer().port
        log.msg("Connected to %s:%s" %(self.chost,self.cport), system='CLIENT')

        #
        self.loop = LoopingCall(self.keepalive)
        self.loop.start(60, False)

        # Register name
        name='smarting'
        log.msg("Registering name '%s'" %(name,), system='CLIENT')
        self.send(Event('name',name))

        # Register events
        evlist = self.client.events
        log.msg("Registering events %s" %(evlist), system='CLIENT')
        self.send(Event('events', *evlist))

    def connectionLost(self, reason):
        self.loop.stop()
        log.msg("Lost connection with %s:%s" %(self.chost,self.cport), system='CLIENT')

    def lineReceived(self, data):
        if not len(data):
            return

        event = Event(data)
        log.msg(event)

    def keepalive(self):
        self.transport.write('ping\n')

    def send(self, data):
        self.transport.write(data.dump()+'\n')



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

    def clientConnectionLost(self, connector, reason):
        log.msg('Lost connection.', reason.getErrorMessage())
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        log.msg('Connection failed.', reason.getErrorMessage())
        ReconnectingClientFactory.clientConnectionFailed(self, connector,
                                                         reason)



class Client(object):

    def __init__(self,host,port):
        self.host = host
        self.port = port

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

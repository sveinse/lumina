import os,sys,re

from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from twisted.internet.defer import Deferred

from core import Event,Core


class TimeoutException(Exception):
    pass


class EventProtocol(LineReceiver):
    noisy = False
    delimiter='\n'
    timeout=15

    def connectionMade(self):
        self.ip = "%s:%s" %(self.transport.getPeer().host,self.transport.getPeer().port)
        self.name = self.ip
        self.events = []
        self.actions = []
        self.requests = { }
        log.msg("Connect from %s" %(self.ip,), system='CTRL')


    def connectionLost(self, reason):
        log.msg("Lost connection from '%s' (%s)" %(self.name,self.ip), system='CTRL')
        if len(self.events):
            self.parent.remove_events(self.events)
        if len(self.actions):
            self.parent.remove_actions(self.actions)
        # FIXME: Revoke all pending requests. Call errback?


    def lineReceived(self, data):
        ''' Handle messages from the clients '''

        # Empty lines are simply ignored
        if not len(data):
            return

        try:
            event = Event().parse(data)
            log.msg("   -->  %s" %(event,), system=self.name)
        except SyntaxError as e:
            log.msg("Protcol error. %s" %(e.message))
            return

        # -- Register client name
        if event.name == 'name':
            self.name = event.args[0]
            log.msg("Client %s identified as '%s'" %(self.ip,self.name), system='CTRL')
            return

        # -- Register client events
        elif event.name == 'events':
            evlist = event.args[:]
            if len(evlist):
                self.events = evlist
                self.parent.add_events(evlist)
            return

        # -- Register client actions
        elif event.name == 'actions':
            evlist = event.args[:]
            if len(evlist):
                self.actions = evlist
                actions = {}
                for a in evlist:
                    actions[a] = lambda a : self.send(a)
                self.parent.add_actions(actions)
            return

        # -- Handle 'exit' event
        elif event.name == 'exit':
            self.transport.loseConnection()
            return

        # -- Handle error to a former request
        elif event.name == 'error':

            # FIXME: Make sure the Event() parser is able to produce proper failure object.
            #        Perhaps Event() should make Exceptions upon receiving error frames
            name = event.args[0]
            request = self.requests[name]
            d = request['defer']
            request['timer'].cancel()
            del self.requests[name]
            d.errback(event)
            return

        # -- Handle a reply to a former request
        elif event.name in self.requests:
            request = self.requests[event.name]
            d = request['defer']
            request['timer'].cancel()
            del self.requests[event.name]

            # FIXME: Perhaps the payload should be a separate object(type), not the event itself?
            d.callback(event)
            return

        # -- Special @ notation which makes the controller execute the incoming data as action
        elif event.name.startswith('@'):

            def raw_reply(reply,cls,event):
                cls.transport.write(">>> %s\n" %(str(reply),))

            newevent = Event(event.name[1:],*event.args,**event.kw)
            fn = self.parent.get_actionfn(newevent.name)
            if not fn:
                self.transport.write('ERR: Event not found. Ignoring %s\n',newevent)
                return

            try:
                self.transport.write("<<< %s\n" %(newevent,))
                result = fn(newevent)
                if isinstance(result, Deferred):
                    result.addCallback(raw_reply, self, newevent)
                    result.addErrback(raw_reply, self, newevent)
                    return
                else:
                    raw_reply(result, self, newevent)
                    return
            except Exception as e:
                raw_reply(e, self, newevent)

                # You need this for debugging
                raise

        # -- A new incoming (async) event.
        else:
            self.parent.handle_event(event)


    # -- Send an action to the client
    def send(self, event):
        d = Deferred()
        self.requests[event.name] = {
            'defer': d,
            'timer': reactor.callLater(self.timeout, self.timedout, event),
        }
        log.msg("   <--  %s" %(event,), system=self.name)
        self.transport.write(event.dump()+'\n')
        return d


    # -- Action timer handler
    def timedout(self, event):
        log.msg('   -->  TIMEOUT %s' %(event,), system=self.name)
        request = self.requests[event.name]
        d = p['defer']
        del self.requests[event.name]

        # FIXME: See error handler response and make similar setup
        d.errback(TimeoutException())



class EventFactory(Factory):
    noisy = False

    def buildProtocol(self, addr):
        proto = EventProtocol()
        proto.parent = self.parent
        return proto



class Controller(Core):

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
            log.msg("%s  --  Unregistered" %(event), system='CTRL')
            return None

        # Known event?
        if event.name not in self.jobs:
            log.msg("%s  --  Ignored, no job handler" %(event), system='CTRL')
            #log.msg("   No job for event '%s', ignoring" %(event.name), system='CTRL')
            return None

        log.msg("%s" %(event), system='CTRL')

        # Get the job and run it
        job = self.jobs[event.name]
        job.event = event
        self.run_job(job)

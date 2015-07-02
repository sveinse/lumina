import os,sys,re

from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from twisted.internet.defer import Deferred

from core import Event,JobBase,Job,Action


class EventProtocol(LineReceiver):
    noisy = False
    delimiter='\n'


    def connectionMade(self):
        self.ip = "%s:%s" %(self.transport.getPeer().host,self.transport.getPeer().port)
        self.name = self.ip
        self.events = []
        self.actions = []
        self.pending = { }
        log.msg("Connect from %s" %(self.ip,), system='CTRL')
        self.factory.addClient(self)


    def connectionLost(self, reason):
        log.msg("Lost connection from '%s' (%s)" %(self.name,self.ip), system='CTRL')
        if len(self.events):
            self.factory.controller.remove_events(self.events)
        if len(self.actions):
            self.factory.controller.remove_actions(self.actions)
        # TODO: Revoke all pending requests. Call errback?
        self.factory.removeClient(self)


    def lineReceived(self, data):
        if not len(data):
            return

        event = Event(data)
        log.msg("   -->  %s" %(event,), system=self.name)

        # -- Register client name
        if event.name == 'name':
            self.name = event.args[0]
            log.msg("Client %s identified as '%s'" %(self.ip,self.name), system='CTRL')

        # -- Register client events
        elif event.name == 'events':
            evlist = event.args[:]
            if len(evlist):
                self.events = evlist
                self.factory.controller.add_events(evlist)

        # -- Register client actions
        elif event.name == 'actions':
            evlist = event.args[:]
            if len(evlist):
                self.actions = evlist
                actions = {}
                for a in evlist:
                    actions[a] = lambda a : self.send(a)
                self.factory.controller.add_actions(actions)

        # -- Handle 'exit' event
        elif event.name == 'exit':
            self.transport.loseConnection()

        # -- Handle a reply to a former action
        elif event.name in self.pending:
            p = self.pending[event.name]
            d = p['defer']
            p['timer'].cancel()
            del self.pending[event.name]
            d.callback(event)

        # -- A new event
        else:
            self.factory.controller.handle_event(event)


    # -- Send an action to the client
    def send(self, event):
        d = Deferred()
        self.pending[event.name] = {
            'defer': d,
            'timer': reactor.callLater(5, self.timeout, event),
            }
        log.msg("   <--  %s" %(event,), system=self.name)
        self.transport.write(event.dump()+'\n')
        return d


    # -- Action timer handler
    def timeout(self, event):
        log.msg('Timeout on %s' %(event,), system=self.name)
        p = self.pending[event.name]
        d = p['defer']
        del self.pending[event.name]
        d.errback(event)



class EventFactory(Factory):
    noisy = False
    protocol = EventProtocol

    def __init__(self):
        self.clients = [ ]

    def addClient(self, client):
        self.clients.append(client)

    def removeClient(self, client):
        self.clients.remove(client)



class Controller(object):

    def __init__(self,port):
        self.port = port
        self.inprogress = False
        self.currentjob = None
        self.currentaction = None
        self.queue = []
        self.events = []
        self.actions = {}
        self.jobs = {}


    def setup(self):

        # Setup socket factory
        self.factory = EventFactory()
        self.factory.controller = self
        reactor.listenTCP(self.port, self.factory)


    def add_events(self, events):
        ''' Add to the list of known events'''

        log.msg("Registering events: %s" %(tuple(events),), system='CTRL')
        for name in events:
            if name in self.events:
                raise TypeError("Event '%s' already exists" %(name))
            self.events.append(name)


    def remove_events(self, events):
        ''' Remove from the list of known events'''

        log.msg("De-registering events: %s" %(tuple(events),), system='CTRL')
        for name in events:
            if name not in self.events:
                raise TypeError("Unknown event '%s'" %(name))
            self.events.remove(name)


    def add_actions(self, actions):
        ''' Add to the dict of known action and register their callback fns '''

        log.msg("Registering actions: %s" %(tuple(actions.keys()),), system='CTRL')
        for (name,fn) in actions.items():
            if name in self.actions:
                raise TypeError("Action '%s' already exists" %(name))
            self.actions[name] = fn


    def remove_actions(self, actions):
        ''' Add to the dict of known action and register their callback fns '''

        log.msg("De-registering actions: %s" %(tuple(actions),), system='CTRL')
        for name in actions:
            if name not in self.actions:
                raise TypeError("Unknown action '%s'" %(name))
            del self.actions[name]


    def add_jobs(self, jobs):
        ''' Add list of jobs '''

        log.msg("Registering handlers for: %s" %(tuple(jobs.keys()),), system='CTRL')
        for (name,actions) in jobs.items():
            #if name not in self.events:
            #    raise TypeError("Job '%s' is not an known event" %(name))
            if name in self.jobs:
                raise TypeError("Job '%s' already exists" %(name))

            # This is done to allow job lists to be specified as text lists or lists
            if isinstance(actions, JobBase):
                job = actions
            else:
                job = Job( actions )
            self.jobs[name] = job


    def handle_event(self, event):
        ''' Event dispatcher '''

        #if not event:
        #    return None
        #if not isinstance(event,Event):
        #    event=Event(event)

        #log.msg("%s" %(event), system='CTRL')

        # Is this a registered event?
        if event.name not in self.events:
            log.msg("%s  --  Unregistered" %(event), system='CTRL')
            return None

        # Known event?
        if event.name not in self.jobs:
            log.msg("%s  --  Ignored, no job handler" %(event), system='CTRL')
            #log.msg("   No job for event '%s', ignoring" %(event.name), system='CTRL')
            return None

        # Get the job
        job = self.jobs[event.name]
        job.event = event
        return self.run_job(job)


    def run_job(self,job):
        ''' Run the given job '''

        # If a job is running, put the new one in a queue
        if job.isempty():
            log.msg("%s  --  Empty job" %(job.event), system='CTRL')
            #log.msg("   Empty job, skipping", system='CTRL')
            return
        self.queue.append(job)
        log.msg("%s  --  %s" %(job.event,job), system='CTRL')
        #log.msg("   -- %s" %(job), system='CTRL')

        if not self.inprogress:
            return self._run_next_action()


    def _run_next_action(self,result=None):
        ''' Internal handler for processing actions in a job '''
        #print "core::run_next_action(result=%s)" %(result)

        self.inprogress = True
        while True:

            # Start the job if no jobs are running
            if self.currentjob is None:

                # No more jobs. Stop
                if len(self.queue) == 0:
                    self.inprogress = False
                    return result

                # Start the job by getting the next object's iterator instance
                self.currentjob = self.queue.pop(0).__iter__()
                self.currentaction = None

            try:
                # Save the previous result (JobFn needs this for yield/send)
                prevresult = None
                if self.currentaction:
                    prevresult = self.currentaction.result
                self.currentjob.prevresult = prevresult

                # Get the next action object
                action = self.get_action(self.currentjob.next())
                self.currentaction = action

                # Execute the given action object (if valid)
                if action:
                    log.msg("   --- RUN %s" %(action), system='CTRL')
                    action.event = self.currentjob.event
                    result = action.execute()

                    # If a Deferred object is returned, we set to call this function when the
                    # results from the operation is ready
                    if isinstance(result, Deferred):
                        result.addCallback(self._run_next_action)
                        result.addErrback(self._run_next_action) # <-- Fixme. This makes the
                                                                 # the job continue on errors
                        return result

            except StopIteration:
                # This will cause the function to evaluate the queue and start over if more
                # to do.
                self.currentjob = None
                self.currentaction = None
                log.msg("   -- DONE", system='CTRL')



    def get_action(self,name):
        ''' Get action object from name and set its function callback '''

        if not name:
            return None

        # Make an action object of the specified name
        action = Action(name=name, fn=None)

        # Known action?
        if action.name not in self.actions:
            log.msg("Unknown action '%s', ignoring" %(action.name), system='CTRL')
            return None

        # Set the function handler
        action.fn = self.actions[action.name]
        return action

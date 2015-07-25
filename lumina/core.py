# -*- python -*-
#
# 2015.04.05
# Notater:
#   - Bor man implementere linking til parent/mother objektet, slik at man f.eks. kan holde
#     metrics, som hvor mange ganger et event har blitt fyrt av?
#
from twisted.internet.defer import Deferred
from twisted.python import log
from twisted.internet import reactor

from types import *

from event import Event


# FIXME: Do we still need this class?
class Action(Event):
    ''' Action handler object. '''

    def __init__(self, name=None, fn=None, *args, **kw):
        Event.__init__(self,name,*args,**kw)
        self.executed = False
        self.result = None
        self.fn = fn
        self.event = None

    def __repr__(self):
        (s,t,r) = ([str(a) for a in self.args],'','')
        for (k,v) in self.kw.items():
            s.append("%s=%s" %(k,v))
        if s:
            t=' {' + ','.join(s) + '}'
        if self.executed:
            r=' :%s' %(self.result)
        return "<ACT:%s%s%s>" %(self.name,t,r)

    def _store_result(self,result):
        self.result = result
        self.executed = True
        return result

    def execute(self):
        result = self.fn(self)
        if isinstance(result, Deferred):
            result.addCallback(self._store_result)
        else:
            self._store_result(result)
        return result


# FIXME: Do we still need this class?
class JobBase(object):
    pass


# FIXME: Do we still need this class?
class Job(JobBase):
    ''' Job collection class. Accepts a list of actions to execute. '''

    def __init__(self, actions, name=None):
        self.name = name
        self.actions = tuple()
        if isinstance(actions, list) or isinstance(actions, tuple):
            self.actions = tuple(actions)
        elif actions is not None:
            self.actions = (actions,)

    def __repr__(self):
        (s,n) = ('','')
        if self.actions:
            sl = [ str(s) for s in self.actions ]
            s=' {' + ','.join(sl) + '}'
        if self.name:
            n = ':%s' %(self.name)
        return "<JOB%s%s>" %(n,s)

    def isempty(self):
        return len(self.actions) == 0

    def __iter__(self):
        self.running = self.actions.__iter__()
        self.subjob = None
        self.prevresult = None
        return self

    def next(self):
        #print "%s::next()   running=%s   subjob=%s" %(self,self.running,self.subjob)
        while True:

            # Getting next action from a sub-job. Return any action returned by the sub-job.
            # If None is returned, the sub-job is complete and we must proceed our own list of
            # jobs/actions.
            if self.subjob:
                try:
                    # Send the prevresult down to the subjob (prevresult is updated by Core._run_next_action())
                    self.subjob.prevresult = self.prevresult
                    return self.subjob.next()
                except StopIteration:
                    self.subjob = None

            try:
                # Get the next item. It is done when StopIteration is raised
                item = self.running.next()

                # If the item is a Job class, then it represents a subjob which must be
                # traversed accordingly. Else the item can be returned as the next object
                if isinstance(item, JobBase):
                    self.subjob = item.__iter__()
                else:
                    return item

            # DONE. If there are no more jobs left in list, raise StopIteration to indicate completion.
            except StopIteration:
                self.running = None
                self.subjob = None
                self.prevresult = None
                raise



# FIXME: Do we still need this class?
class JobFn(JobBase):
    ''' Job collection class for running a generator function. '''

    def __init__(self, fn, name=None):
        self.name = name
        self.fn = fn

    def __repr__(self):
        n=''
        if self.name:
            n = ':%s' %(self.name)
        return "<JOB%s %s>" %(n,self.fn)

    def isempty(self):
        return False

    def __iter__(self):
        self.running = None
        self.subjob = None
        self.prevresult = None
        return self

    def next(self):
        #print "%s::next()   running=%s   subjob=%s" %(self,self.running,self.subjob)
        while True:

            # Getting next action from a sub-job. Return any action returned by the sub-job.
            # If None is returned, the sub-job is complete and we must proceed our own list of
            # jobs/actions.
            if self.subjob:
                try:
                    # Send the prevresult down to the subjob (prevresult is updated by Core._run_next_action())
                    self.subjob.prevresult = self.prevresult
                    return self.subjob.next()
                except StopIteration:
                    self.subjob = None

            try:
                # Get the next item. It is done if StopIteration is raised
                if self.running is None:
                    # This will fail if generator function is not function:
                    #    TypeError: 'xxx' object is not callable
                    # If function is not a generator then it fails with:
                    #    AttributeError: 'xxx' object has no attribute 'next'
                    self.running = self.fn()
                    item = self.running.next()
                else:
                    # Send the results from the previous action. prevresult is updated by
                    # Core._run_next_action(), which is somewhat a hack. IMHO have to be this way as
                    # this class don't know anything about Action() objects here.
                    item = self.running.send(self.prevresult)

                # If the item is a Job class, then it represents a subjob which must be
                # traversed accordingly. Else the item can be returned as the next object
                if isinstance(item, JobBase):
                    self.subjob = item.__iter__()
                else:
                    return item

            # DONE. If there are no more jobs left in list, raise StopIteration to indicate completion.
            except StopIteration:
                self.running = None
                self.subjob = None
                self.prevresult = None
                raise



class Core(object):
    system='CORE'


    def __init__(self):
        self.events = []
        self.commands = {}
        self.endpoints = []
        self.jobs = {}

        # Job handler
        self.queue = []
        self.currentjob = None
        self.inprogress = False
        self.currentcommand = None


    # --- EVENTS
    def add_events(self,events):
        ''' Add to the list of known events'''

        if isinstance(events, dict):
            events=events.keys()

        log.msg("Registering %s events" %(len(events),), system=self.system)
        for name in events:
            if name in self.events:
                raise TypeError("Event '%s' already exists" %(name))
            self.events.append(name)

    def remove_events(self, events):
        ''' Remove from the list of known events'''

        log.msg("De-registering %s events" %(len(events),), system=self.system)
        for name in events:
            if name not in self.events:
                raise TypeError("Unknown event '%s'" %(name))
            self.events.remove(name)


    # --- COMMANDS
    def add_commands(self, commands):
        ''' Add to the dict of known commands and register their callback fns '''

        log.msg("Registering %s commands" %(len(commands),), system=self.system)
        for (name,fn) in commands.items():
            if name in self.commands:
                raise TypeError("Command '%s' already exists" %(name))
            self.commands[name] = fn

    def remove_commands(self, commands):
        ''' Remove from the dict of known commands '''

        log.msg("De-registering %s commands" %(len(commands),), system=self.system)
        for name in commands:
            if name not in self.commands:
                raise TypeError("Unknown command '%s'" %(name))
            del self.commands[name]

    def get_commandfn(self, command):
        ''' Get the command handler function '''
        return self.commands.get(command)


    # --- JOBS
    def add_jobs(self,jobs):
        ''' Add list of jobs '''

        log.msg("Registering %s handlers for events" %(len(jobs),), system=self.system)
        for (name,commands) in jobs.items():
            if name in self.jobs:
                raise TypeError("Job '%s' already exists" %(name))

            # This is done to allow job lists to be specified as text lists or lists
            if isinstance(commands, JobBase):
                job = commands
            else:
                job = Job( commands )
            self.jobs[name] = job


    # --- ENDPOINT REGISTRATION
    def register(self,endpoint):
        log.msg("===  Registering endpoint %s" %(endpoint.name), system=self.system)
        endpoint.configure()
        endpoint.add_eventcallback(self.handle_event)
        self.add_events(endpoint.get_events())
        self.add_commands(endpoint.get_commands())
        endpoint.setup()
        reactor.addSystemEventTrigger('before','shutdown',endpoint.close)
        self.endpoints.append(endpoint)


    # --- JOB HANDLING

    # FIXME: Add support for parallel execution
    def run_job(self,job):
        ''' Run the given job '''

        # If a job is running, put the new one in a queue
        if job.isempty():
            log.msg("%s  --  Empty job" %(job.event), system=self.system)
            #log.msg("   Empty job, skipping", system=self.system)
            return
        self.queue.append(job)
        log.msg("%s  --  %s" %(job.event,job), system=self.system)
        #log.msg("   -- %s" %(job), system=self.system)

        if not self.inprogress:
            return self._run_next_action()


    # FIXME: Add support for parallel execution
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
                self.currentcommand = None

            try:
                # Save the previous result (JobFn needs this for yield/send)
                prevresult = None
                if self.currentcommand:
                    prevresult = self.currentcommand.result
                self.currentjob.prevresult = prevresult

                # Get the next action object
                name = self.currentjob.next()
                action = None
                if name:
                    action = Action().parse_str(name)
                    action.fn = self.get_commandfn(action.name)
                    if action.fn is None:
                        action = None
                self.currentcommand = action

                # Execute the given action object (if valid)
                if action:
                    log.msg("   --- RUN %s" %(action), system=self.system)
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
                self.currentcommand = None
                log.msg("   -- DONE", system=self.system)

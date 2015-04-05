
# 2015.04.05
# Notater:
#   - Bor man implementere linking til parent/mother objektet, slik at man f.eks. kan holde
#     metrics, som hvor mange ganger et event har blitt fyrt av?
#
from twisted.internet.defer import Deferred
from twisted.python import log
#from callback import Callback
#from job import Event, Action, Job
import re
from types import *



class Event(object):
    ''' Event object.
           event = Event(name,*args,**kw)

        Event name text syntax:
           'foo'
           'bar{1,2}'
           'nul{arg1=foo,arg2=bar}'
           'nul{arg1=foo,arg2=bar,5}'
    '''
    def __init__(self, name, *args, **kw):
        self.parse(name,*args,**kw)

    def __repr__(self):
        (s,t) = ([str(a) for a in self.args],'')
        for (k,v) in self.kw.items():
            s.append("%s=%s" %(k,v))
        if s:
            t=' {' + ','.join(s) + '}'
        return "<EVENT:%s%s>" %(self.name,t)

    def parse(self, name, *args, **kw):
        m = re.match(r'^([^{}]+)({(.*)})?$', name)
        if not m:
            raise SyntaxError("Invalid syntax '%s'" %(name))
        self.name = m.group(1)
        self.args = []
        self.kw = {}
        opts = m.group(3)
        if opts:
            for arg in opts.split(','):
                if '=' in arg:
                    k = arg.split('=')
                    self.kw[k[0]] = k[1]
                else:
                    self.args.append(arg)
        # Update optional variable arguments from constructor. Append the args, and update
        # the kw args. This will override any colliding kw options that might have been present
        # in the text string.
        self.args += args
        self.kw.update(kw)



class Action(Event):
    ''' Action handler object. '''

    def __init__(self, name, fn, *args, **kw):
        self.parse(name,*args,**kw)
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
        return "<ACTION:%s%s%s>" %(self.name,t,r)

    def _store_result(self,result):
        self.result = result
        self.executed = True
        return result

    def execute(self):
        log.msg("Run   %s" %(self), system='ACTION')
        result = self.fn(self)
        if isinstance(result, Deferred):
            result.addCallback(self._store_result)
        else:
            self._store_result(result)
        return result



class JobBase(object):
    pass


class Job(JobBase):
    ''' Job collection class. Accepts a list of actions to execute. '''

    def __init__(self, actions, name=None):
        self.name = name
        self.actions = [ ]
        if not isinstance(actions, list) and not isinstance(actions, tuple):
            self.actions = (actions,)
        else:
            self.actions = tuple(actions)

    def __repr__(self):
        (s,n) = ('','')
        if self.actions:
            sl = [ str(s) for s in self.actions ]
            s=' {' + ','.join(sl) + '}'
        if self.name:
            n = ':%s' %(self.name)
        return "<JOB%s%s>" %(n,s)

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

    def __init__(self):
        self.inprogress = False
        self.currentjob = None
        self.currentaction = None
        self.queue = []
        self.events = []
        self.actions = {}
        self.jobs = {}


    def add_events(self,events):
        ''' Add to the list of known events'''

        log.msg("Registering events: %s" %(tuple(events),), system='EVENT ')
        for name in events:
            if name in self.events:
                raise TypeError("Event '%s' already exists" %(name))
            self.events.append(name)


    def add_actions(self,actions):
        ''' Add to the dict of known action and register their callback fns '''

        log.msg("Registering actions: %s" %(tuple(actions.keys()),), system='ACTION')
        for (name,fn) in actions.items():
            if name in self.actions:
                raise TypeError("Action '%s' already exists" %(name))
            self.actions[name] = fn


    def add_jobs(self,jobs):
        ''' Add list of jobs '''

        log.msg("Registering jobs: %s" %(tuple(jobs.keys()),), system='JOB   ')
        for (name,actions) in jobs.items():
            if name not in self.events:
                raise TypeError("Job '%s' is not an known event" %(name))
            if name in self.jobs:
                raise TypeError("Job '%s' already exists" %(name))
            if isinstance(actions, JobBase):
                job = actions
            else:
                job = Job( actions )
            self.jobs[name] = job


    def handle_event(self,event):
        ''' Event dispatcher '''

        if not event:
            return None
        if not isinstance(event,Event):
            event=Event(event)

        log.msg("%s" %(event), system='EVENT ')

        # Is this a registered event?
        if event.name not in self.events:
            log.msg("   Unregistered event '%s'" %(event.name), system='EVENT ')

        # Known event?
        if event.name not in self.jobs:
            log.msg("   No job for event '%s', ignoring" %(event.name), system='EVENT ')
            return None

        # Get the job
        job = self.jobs[event.name]
        job.event = event
        return self.run_job(job)


    def run_job(self,job):
        ''' Run the given job '''

        # If a job is running, put the new one in a queue
        if not job:
            log.msg("   -- DONE", system='JOB   ')
            return
        self.queue.append(job)
        log.msg("   -- %s" %(job), system='JOB   ')
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
                    action.event = self.currentjob.event
                    result = action.execute()

                    # If a Deferred object is returned, we set to call this function when the
                    # results from the operation is ready
                    if isinstance(result, Deferred):
                        result.addCallback(self._run_next_action)
                        return result

            except StopIteration:
                # This will cause the function to evaluate the queue and start over if more
                # to do.
                self.currentjob = None
                self.currentaction = None
                log.msg("   -- DONE", system='JOB   ')


    def get_action(self,name):
        ''' Get action object from name and set its function callback '''

        if not name:
            return None

        # Make an action object of the specified name
        action = Action(name=name, fn=None)

        # Known action?
        if action.name not in self.actions:
            log.msg("Unknown action '%s', ignoring" %(action.name), system='ACTION')
            return None

        # Set the function handler
        action.fn = self.actions[action.name]
        return action






################################################################
#
#  TESTING
#
################################################################
if __name__ == "__main__":

    # -----------------------------------------------
    def test_core():
        from twisted.internet import reactor
        from twisted.internet import task
        from twisted.python import log, syslog
        import sys


        log.startLogging(sys.stdout)

        def later(args):
            d = 'LATER'
            args.callback('REPLY')

        def fa_done(args):
            d = 'DONE'
            print "\t\tFA DONE: ",args,d
            return d

        def fa(args):
            # Create a deferred response which will occur 0.2 seconds later
            print "\t\tFA DFER: ",args
            d = Deferred()
            d.addCallback(fa_done)
            task.deferLater(reactor, 0.2, later, d)
            return d

        def fb(args):
            # Reply immediately
            d = 'NOW'
            print "\t\tFB DONE: ",args,d
            return d

        def fc(args):
            # Reply immediately
            d = 'OK'
            print "\t\tFC DONE: ",args,args.event,d
            return d

        def gen():
            print "GEN PRE"
            result = yield 'fa'
            print "GEN STEP1=%s" %(result,)
            if result:
                print "GEN STEP2"
                result = yield 'fb{12}'
                print "GEN STEP3=%s" %(result,)
                yield 'fa'
                print "GEN STEP4=%s" %(result,)
            print "GEN DONE"

        def gen2():
            print "GEN2 PRE"
            result = yield 'fa'
            print "GEN2 STEP1=%s" %(result,)
            result = yield Job( ('fa','fa') )
            print "GEN DONE=%s" %(result)

        c = Core()

        # Register name of events
        c.add_events( ( 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm' ) )

        # Register actions and their handlers
        c.add_actions( {
            'fa': fa,
            'fb': fb,
            'fc': fc,
        } )

        ja = Job( ('fb','fb','fa'), name='h-rule' )
        jf = JobFn( gen, name='i')

        # Register jobs
        c.add_jobs( {
            'a' : 'fa',           # Test deferred handling
            'b' : 'fb',           # Test non-deferred handling
            'c' : None,           # Test empty rule
            'd' : tuple(),        # Test other empty rule
            'e' : ('fa', ),       # Testing list
            'f' : ('fa', 'fb'),   # Testing list2
            'g' : ('fa', 'fa'),   # Testing list3 (two deferreds)
            'h' : ('fb{42}'),     # Testing args in jobs
            'i' : ('fc'),         # Testing args in event
            'j' : ja,             # Testing Job() types
            'k' : jf,             # Testing generators
            'l' : Job( ('fa',ja,ja,jf), name='j'),   # Testing recursive jobs
            'm' : JobFn( gen2 ),  # Testing JobFn() yielding Job()s
        } )
        testlist = ( 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i{12,arg=34}', 'j', 'k', 'l', 'm' )


        def start(fn):
            print "\n\t\t\t\t** START **", fn
            c.handle_event(fn)
        def stop():
            reactor.stop()

        t = 1
        for test in testlist:
            task.deferLater(reactor, t, start, test)
            t += 1.5
        task.deferLater(reactor, t, stop)

        print c.events
        print c.actions
        print c.jobs

        reactor.run()


    test_core()

    import sys
    sys.exit(0)

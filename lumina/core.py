from twisted.internet.defer import Deferred
from twisted.python import log
#from callback import Callback
#from job import Event, Action, Job
import re
from types import *


class Event(object):
    def __init__(self,event,*args):
        self.event = event
        self.args = args

    def __repr__(self):
        return "<EVENT %s>" %(self.event)



class Action(object):
    def __init__(self, action):
        self.parse(action)
        self.executed = False

    def __repr__(self):
        (s,t,r) = (self.args[:],'','')
        for (k,v) in self.kw.items():
            s.append("%s=%s" %(k,v))
        if s:
            t=' ' + ' '.join(s)
        if self.executed:
            r=' =%s' %(self.result)
        return "<ACTION %s%s%s>" %(self.action,t,r)

    def parse(self, text):
        m = re.match(r'^([^{}]+)({(.*)})?$', text)
        if not m:
            raise SyntaxError("Invalid syntax on action '%s'" %(text))
        self.action = m.group(1)
        self.args = []
        self.kw = {}
        args = m.group(3)
        if args:
            for arg in args.split(','):
                if '=' in arg:
                    key = arg.split('=')
                    self.kw[key[0]] = key[1]
                else:
                    self.args.append(arg)

    def setresult(self, result):
        self.executed = True
        self.result = result



class Job(object):
    def __init__(self, actions):
        if not isinstance(actions, list) and not isinstance(actions, tuple):
            self.actions = (actions,)
        else:
            self.actions = tuple(actions)

    def __repr__(self):
        return "<JOB %s>" %(self.actions,)

    def __iter__(self):
        self.running = self.actions.__iter__()
        self.subjob = None
        return self

    def next(self):
        #print "%s::next()   running=%s   subjob=%s" %(self,self.running,self.subjob)
        while True:

            # Getting next action from a sub-job. Return any action returned by the sub-job.
            # If None is returned, the sub-job is complete and we must proceed our own list of
            # jobs/actions.
            if self.subjob:
                try:
                    return self.subjob.next()
                except StopIteration:
                    self.subjob = None

            try:
                # Get the next item. It is done when StopIteration is raised
                item = self.running.next()

                # If it is action or string, return it.
                if isinstance(item, Action) or isinstance(item, str):
                    return item

                # ..else it is a sub-job which must be traversed accordingly
                self.subjob = item.__iter__()
                # continue while loop after this

            # DONE. If there are no more jobs left in list, raise StopIteration to indicate completion.
            except StopIteration:
                self.running = None
                self.subjob = None
                raise



class JobF(object):
    def __init__(self, fn):
        self.fn = fn

    def __repr__(self):
        return "<JOB %s>" %(self.fn,)

    def __iter__(self):
        self.running = None
        self.subjob = None
        self.lastaction = None
        return self

    def next(self):
        #print "%s::next()   running=%s   subjob=%s" %(self,self.running,self.subjob)
        while True:

            # Getting next action from a sub-job. Return any action returned by the sub-job.
            # If None is returned, the sub-job is complete and we must proceed our own list of
            # jobs/actions.
            if self.subjob:
                try:
                    self.lastaction = None
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
                    # Send the results from the previous action
                    item = self.running.send(self.lastaction.result)

                # Special treatment: If a string, promote it to Action() because its result is needed in the
                # next iteration. If this promotion is omitted, the generator must yield Action() objects.
                # Not sure which is best or worst.
                #if isinstance(item, str):
                #    item = Action( item )

                # Save item because it is needed to send the back the results on the next yield.
                # This is somewhat of a hack, as this function does not really produce any result from
                # Actions() object, it just serializes them.
                self.lastaction = item

                # If it is action or string, return it.
                if isinstance(item, Action) or isinstance(item, str):
                    return item

                # ..else it is a sub-job which must be traversed accordingly
                self.subjob = item.__iter__()
                # continue while loop after this

            # DONE. If there are no more jobs left in list, raise StopIteration to indicate completion.
            except StopIteration:
                self.running = None
                self.subjob = None
                self.lastaction = None
                raise



class Core(object):

    def __init__(self):
        self.rules = {}
        self.actions = {}
        self.currentjob = None
        self.queue = []
        self.pending = False


    def addrules(self,rules):
        for (name,actions) in rules.items():
            if name in self.rules:
                raise TypeError("Rule for '%s' already exists" %(name))
            if actions is None:
                job = None
            elif isinstance(actions, str):
                job = Job( Action(actions) )
            elif isinstance(actions, tuple) or isinstance(actions, list):
                job = Job( [ Action(a) for a in actions ] )
            elif not isinstance(actions, Job):
                job = Job( actions )
            self.rules[name] = job


    def addactions(self,actions):
        for (name,fn) in actions.items():
            if name in self.actions:
                raise TypeError("Action '%s' already exists" %(name))
            self.actions[name] = fn


    def handle_event(self,event):
        ''' Event dispatcher '''

        if not event:
            return
        if isinstance(event,str):
            event=Event(event)

        log.msg("%s" %(event), system='EVENT ')

        # Known event?
        if event.event not in self.rules:
            log.msg("   Unregistered event '%s', ignoring" %(event.event), system='EVENT ')
            return

        # Execute job
        job = self.rules[event.event]
        #log.msg("   -> %s" %(job), system='EVENT ')
        self.run_job(job)


    def run_job(self,job):
        ''' Run the given job '''

        # If a job is running, put the new one in a queue
        if not job:
            log.msg("   -- IGNORED", system='EVENT ')
            return
        self.queue.append(job)
        log.msg("   -- %s" %(job), system='EVENT ')
        if not self.pending:
            self._run_next_action()


    def _run_next_action(self,result=None):
        ''' Internal handler for processing actions in a job '''
        #print "core::run_next_action(result=%s)" %(result)

        self.pending = True
        while True:

            # Start the job if no jobs are running
            if self.currentjob is None:

                # No more jobs. Stop
                if len(self.queue) == 0:
                    self.pending = False
                    return

                # Start the job
                self.currentjob = self.queue.pop(0).__iter__()

            try:
                # Get the next action object
                action = self.currentjob.next()

                # Execute the given action object
                result = self.execute_action(action)

                # If a Deferred object is returned, we set to call this function when the
                # results from the operation is ready
                if isinstance(result, Deferred):
                    result.addCallback(self._run_next_action)
                    return result

            except StopIteration:
                # This will cause the function to evaluate the queue and start over if more
                # to do.
                self.currentjob = None



    def execute_action(self,action):
        ''' Event dispatcher (called by the Action object) '''

        if not action:
            return
        if isinstance(action,str):
            action=Action(action)

        log.msg("%s" %(action), system='ACTION')

        # Known action?
        if action.action not in self.actions:
            log.msg("   Unknown action '%s', ignoring" %(action.action), system='ACTION')
            return

        # Call action
        def save(result):
            action.setresult(result)
            log.msg("%s" %(action), system='ACTION')

        result = self.actions[action.action](action)
        if isinstance(result, Deferred):
            result.addCallback(save)
        else:
            save(result)
        return result







################################################################
#
#  TESTING
#
################################################################
def test1():
    def done(result):
        print "CALLBACK: %s" %(result)

    a = Action('a')
    b = Action('b')

    c = Job( a )
    d = Job( b )
    e = Job( (a,b) )
    f = Job( (a,b,b,a) )
    g = Job( (a,a,a,a) )
    h = Job( tuple() )

    a1 = Job( (a,a) )
    b1 = Job( (b,b) )
    i  = Job( (a1,b1) )

    def gen():
        print "PRE"
        result = yield Action('a')
        print "STEP1=%s" %(result,)
        if result:
            print "STEP2"
            yield Action('b')
        print "STEP3"
        yield Action('c')

    a2 = JobF( gen )
    b2 = Job( (i, a2, f) )

    do = [ c, d, e, f, g, h, i, a2, b2 ]

    for d in do:
        print "JOB:: %s" %(d)
        for o in d:
            print "   ACTION:: %s" %(o)
            o.setresult(True)
        print "========"



def test2():
    from twisted.internet import reactor
    from twisted.internet import task
    from twisted.python import log, syslog
    import sys


    log.startLogging(sys.stdout)

    def tick(d):
        print "\t\t\t\t** TICK **",d
        d.callback('OK')
        print "**DONE**"

    def fa(args):
        print "FA: ",args
        d = Deferred()
        task.deferLater(reactor, 1, tick, d)
        return d

    def fb(args):
        print "FB: ",args
        return 'NOW'
        #d = Deferred()
        #task.deferLater(reactor, 2, tick, d)
        #return d

    c = Core()

    c.addrules( {
        'a' : 'fa',
        'b' : 'fb',
    } )

    c.addactions( {
        'fa': fa,
        'fb': fb,
    } )

    def start(fn):
        print "\t\t\t\t** START **"
        c.handle_event(fn)

    task.deferLater(reactor, 1, start, 'a')
    task.deferLater(reactor, 5, start, 'b')
    reactor.run()



if __name__ == "__main__":

    #test1()
    test2()

    import sys
    sys.exit(0)

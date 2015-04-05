
# 2015.04.05
# Svein pickup:
#
#   - Test h fungerer ikke skikkelig under. Job( ) bør kunne brukes med tekst-argumenter:
#        Job( ('a','b','c{42}'), name='somejob')
#
#   - Test g fungerer ikke, fordi event parameteren er ikke tilgjengelig i actionobjektene
#     Forslaget er å legge eventen inn i Job(), og da må eventen også legges inn i Action()
#     objektene.
#
#   - Bør man klone Job() og/eller Action() objektene når de kjøres? Fordi kjørestatus (result),
#     linking til event, etc. gjelder det tilfellet av den eventen, ikke generelt
#
#   - Bør man implementere linking til parent/mother objektet, slik at man f.eks. kan holde
#     metrics, som hvor mange ganger et event har blitt fyrt av?
#


from twisted.internet.defer import Deferred
from twisted.python import log
#from callback import Callback
#from job import Event, Action, Job
import re
from types import *


#class Event(object):
#    def __init__(self,event,*args):
#        self.event = event
#        self.args = args
#
#    def __repr__(self):
#        return "<EVENT %s>" %(self.event)

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
            t=' ' + ' '.join(s)
        return "<EVENT %s%s>" %(self.name,t)

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
    ''' Action object. Inherited from Event(), but has added functionality
        for keeping track of '''

    def __init__(self, name, *args, **kw):
        self.parse(name,*args,**kw)
        self.executed = False
        self.result = None

    def __repr__(self):
        (s,t,r) = ([str(a) for a in self.args],'','')
        for (k,v) in self.kw.items():
            s.append("%s=%s" %(k,v))
        if s:
            t=' ' + ','.join(s)
        if self.executed:
            r=' :%s' %(self.result)
        return "<ACTION %s%s%s>" %(self.name,t,r)

    def delresult(self):
        self.executed = False
        self.result = None

    def setresult(self, result):
        self.executed = True
        self.result = result



class Job(object):
    def __init__(self, actions, name=None):
        self.name = name
        self.actions = [ ]
        if not isinstance(actions, list) and not isinstance(actions, tuple):
            self.actions = (actions,)
        else:
            self.actions = tuple(actions)

    def __repr__(self):
        s = ''
        if self.actions:
            sl = [ str(s) for s in self.actions ]
            s=' ' + ','.join(sl)
        return "<JOB %s%s>" %(self.name or '',s)

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
    def __init__(self, fn, name=None):
        self.name = name
        self.fn = fn

    def __repr__(self):
        return "<JOB %s%s>" %(self.name or '',self.fn)

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
        self.currentjob = None
        self.queue = []
        self.pending = False

        # NEO
        self.events = []
        self.actions = {}
        self.rules = {}


    def add_events(self,events):
        ''' Add to the list of known events'''

        for name in events:
            if name in self.events:
                raise TypeError("Event '%s' already exists" %(name))
            self.events.append(name)


    def add_actions(self,actions):
        ''' Add to the dict of known action and register their callback fns '''

        for (name,fn) in actions.items():
            if name in self.actions:
                raise TypeError("Action '%s' already exists" %(name))
            self.actions[name] = fn


    def add_rules(self,rules):
        ''' Add list of rules '''

        for (name,actions) in rules.items():
            if name not in self.events:
                raise TypeError("Rule '%s' is not an known event" %(name))
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


    def handle_event(self,event):
        ''' Event dispatcher '''

        if not event:
            return
        if isinstance(event,str):
            event=Event(event)

        log.msg("%s" %(event), system='EVENT ')

        # Stop if we don't know this event
        if event.name not in self.events:
            log.msg("   Unregistered event '%s', ignoring" %(event.name), system='EVENT ')
            return

        # Known event?
        if event.name not in self.rules:
            log.msg("   No rule for event '%s', ignoring" %(event.name), system='EVENT ')
            return

        # Execute job
        job = self.rules[event.name]
        #log.msg("   -> %s" %(job), system='EVENT ')
        self.run_job(job)


    # ----- NEO -----


    def run_job(self,job):
        ''' Run the given job '''

        # If a job is running, put the new one in a queue
        if not job:
            log.msg("   -- DONE", system='EVENT ')
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
                log.msg("   -- DONE", system='EVENT ')


    def execute_action(self,action):
        ''' Event dispatcher (called by the Action object) '''

        if not action:
            return
        if isinstance(action,str):
            action=Action(action)

        log.msg("%s" %(action), system='ACTION')

        # Known action?
        if action.name not in self.actions:
            log.msg("   Unknown action '%s', ignoring" %(action.name), system='ACTION')
            return

        # Call action
        def save(result):
            action.setresult(result)
            log.msg("%s" %(action), system='ACTION')

        result = self.actions[action.name](action)
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
if __name__ == "__main__":


    # -----------------------------------------------
    def test_job():

        def done(result):
            print "CALLBACK: %s" %(result)

        a = Action('a')
        b = Action('b')

        c = Job( a, name='c' )
        d = Job( b, name='d' )
        e = Job( (a,b), name='e' )
        f = Job( (a,b,b,a), name='f' )
        g = Job( (a,a,a,a), name='g' )
        h = Job( tuple(), name='h' )

        a1 = Job( (a,a), name='a1' )
        b1 = Job( (b,b), name='b1' )
        i  = Job( (a1,b1), name='i' )

        def gen():
            print "PRE"
            result = yield Action('a')
            print "STEP1=%s" %(result,)
            if result:
                print "STEP2"
                yield Action('b{12}')
                print "STEP3"
                yield Action('c')

        a2 = JobF( gen, name='a2' )
        b2 = Job( (i, a2, f), name='b2' )

        do = [ c, d, e, f, g, h, i, a2, b2 ]

        for d in do:
            print "JOB:: %s" %(d)
            ol = []
            for o in d:
                print "   ACTION:: %s" %(o)
                o.setresult(True)  # Set this because else the JobF() generator above will fail
                ol.append(o)

            # Erase result to prep the list for the next test
            od = [ o.delresult() for o in ol ]
            print "========"



    # -----------------------------------------------
    def test_core():
        from twisted.internet import reactor
        from twisted.internet import task
        from twisted.python import log, syslog
        import sys


        log.startLogging(sys.stdout)

        def tick(d):
            print "\t\t\t\t** TICK **",d
            d.callback('LATER')
            print "**DONE**"

        def fa(args):
            print "FA: ",args
            d = Deferred()
            task.deferLater(reactor, 0.5, tick, d)
            return d

        def fb(args):
            print "FB: ",args
            return 'NOW'
            #d = Deferred()
            #task.deferLater(reactor, 2, tick, d)
            #return d

        #def gen():
        #    print "PRE"
        #    result = yield Action('a')
        #    print "STEP1=%s" %(result,)
        #    if result:
        #        print "STEP2"
        #        yield Action('b{12}')
        #        print "STEP3"
        #        yield Action('c')

        #a2 = JobF( gen, name='a2' )

        c = Core()

        # Register name of events
        c.add_events( ( 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h' ) )

        # Register actions and their handlers
        c.add_actions( {
            'fa': fa,
            'fb': fb,
        } )

        # Register rules
        c.add_rules( {
            'a' : 'fa',          # Test deferred handling
            'b' : 'fb',          # Test non-deferred handling
            'c' : None,          # Test empty rule
            'd' : ('fa', ),      # Testing list
            'e' : ('fa', 'fb'),  # Testing list2
            'f' : ('fb{42}'),    # Testing args in rules
            'g' : ('fb'),        # Testing args in event
            'h' : Job( ('fb','fb','fa'), name='h-rule' ),
        } )


        def start(fn):
            print "\n\t\t\t\t** START **", fn
            c.handle_event(fn)
        def stop():
            reactor.stop()

        testlist = ( 'a', 'b', 'c', 'd', 'e', 'f', 'g{12}', 'h' )
        t = 1
        for test in testlist:
            task.deferLater(reactor, t, start, test)
            t += 3
        task.deferLater(reactor, t, stop)
        reactor.run()




    #test_job()
    test_core()

    import sys
    sys.exit(0)

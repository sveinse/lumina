# -*- python -*-
import sys,os
sys.path.append(os.path.join(os.path.dirname(__file__),'..'))

from core import *


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

# -*- python -*-

class Callback(object):
    ''' Small class for implementing callback mechanism. Twisted's Deferred() object does not
        support multi-fire, which this object supports.
    '''

    def __init__(self):
        self.callbacks = [ ]
        self.fired = 0

    def addCallback(self, callback, *args, **kw):
        self.callbacks.append( (callback, args, kw) )

    def callback(self, result, condition=None):
        if condition is not None:
            if not condition:
                return
        self.fired += 1
        for cb, args, kw in self.callbacks:
            args = args or ()
            kw = kw or {}
            cb(result, *args, **kw)

    def __str__(self):
        return "<Callback instance; fired=%s, cbs=%s>" %(self.fired,self.callbacks)



#def allCallbacks(*args):
#    ''' Return a Callback() object which will trigger when all the listed callback object
#        has been fired. '''
#    if not args:
#        return None
#    c = Callback()
#    c.remain = len(args)
#    def done(result,c):
#        if c.remain:
#            c.remain -= 1
#        if not c.remain:
#            c.callback(None)
#    for a in args:
#        a.addCallback(done,c)
#    return c




################################################################
#
#  TESTING
#
################################################################
if __name__ == "__main__":
    def f(result):
        print "f()",result

    c = Callback()
    c.addCallback(f)
    c.callback(123)

    print

    a = Callback()
    a.addCallback(f)
    b = Callback()
    b.addCallback(f)
    #d = allCallbacks(a,b)
    #d.addCallback(f)

    a.callback(1)
    b.callback(2)
    print "C"

    class A:
        def f(self,r,a):
            print 'A.f()',r,a

    a = A()
    c = Callback()
    c.addCallback(a.f,12)
    c.callback(42)

# -*- python -*-


# FIXME: Obsoleted?

class Callback(object):
    ''' Small class for implementing callback mechanism. Templated on Twisted's Deferred()
        mechanism, but with support for multi-fire operation.
    '''

    def __init__(self):
        self.callbacks = []
        self.fired = 0


    def addCallback(self, callback, *args, **kw):
        self.callbacks.append((callback, args, kw))


    def callback(self, result, condition=None):
        if condition is not None:
            if not condition:
                return
        self.fired += 1
        for callback, args, kw in self.callbacks:
            args = args or ()
            kw = kw or {}
            callback(result, *args, **kw)


    def __str__(self):
        return "<Callback instance; fired=%s, cbs=%s>" %(self.fired, self.callbacks)



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

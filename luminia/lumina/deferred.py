from twisted.python import log, failure

#from twisted.internet.defer import Deferred
from twisted.python import failure

'''class MyDeferred(Deferred):
    def callback(self, result):
        self.savedcallbacks = self.callbacks[:]
        Deferred.callback(self, result)

    def errback(self, fail=None):
        self.savedcallbacks = self.callbacks[:]
        Deferred.errback(self, fail)

    def reset(self):
        if not self.called:
            return
        self.called = False
        self.callbacks = self.savedcallbacks
'''

def passthru(arg):
    return arg


class MyDeferred:

    def __init__(self):
        self.callbacks = [ ]

    def addCallbacks(self, callback, errback=None,
                     callbackArgs=None, callbackKeywords=None,
                     errbackArgs=None, errbackKeywords=None):
        cbs = ( (callback, callbackArgs, callbackKeywords),
                (errback or (passthru), errbackArgs, errbackKeywords) )
        self.callbacks.append(cbs)
        return self

    def addCallback(self, callback, *args, **kw):
        return self.addCallbacks(callback, callbackArgs=args, callbackKeywords=kw)

    def addErrback(self, errback, *args, **kw):
        return self.addCallbacks(passthru, errback, errbackArgs=args, errbackKeywords=kw)

    def addBoth(self, callback, *args, **kw):
        return self.addCallbacks(callback, callback,
                                 callbackArgs=args, errbackArgs=args,
                                 callbackKeywords=kw, errbackKeywords=kw)

    def callback(self, result):
        self.result = result
        self._runCallbacks()

    def errback(self, fail):
        if fail is None:
            fail = failure.Failure()
        elif not isinstance(fail, failure.Failure):
            fail = failure.Failure(fail)
        self.result = fail
        self._runCallbacks()

    def _runCallbacks(self):
        for item in self.callbacks:

            callback, args, kw = item[ isinstance(self.result, failure.Failure) ]
            args = args or ()
            kw = kw or {}

            try:
                self.result = callback(self.result, *args, **kw)
            except:
                self.result = failure.Failure()

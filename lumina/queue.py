#-*- python -*-
from twisted.internet.defer import Deferred
from twisted.internet import reactor


class Queue(object):

    def __init__(self):
        self.active = None
        self.queue = [ ]
        self.timer = None

    def add(self, *args, **kw):
        ''' Add a new request to the queue. Return a Deferred() object connected to
            the newly created request
        '''
        request = dict(*args,**kw)
        d = Deferred()
        request['defer'] = d
        self.queue.append(request)
        return d

    def get_next(self):
        ''' Return the next request to send and mark it as active. If the queue is
            already active, None will be returned
        '''
        if self.active is not None:
            return None
        if not len(self.queue):
            return None
        self.active = self.queue.pop(0)
        return self.active

    def response(self, data):
        ''' Send response back to caller of the active queued request. The active
            request will be removed
        '''
        if self.timer:
            self.timer.cancel()
            self.timer = None
        (request, self.active) = (self.active, None)
        request['defer'].callback(data)

    def fail(self, reason):
        ''' Send failed (errback) response to the caller of the request. The active
            request will be removed.
        '''
        if self.timer:
            self.timer.cancel()
            self.timer = None
        (request, self.active) = (self.active, None)
        request['defer'].errback(reason)

    def set_timeout(self,timeout,fn,*args,**kw):
        ''' Set a timeout and callback. Calling response() or fail() will cancel
            the timeout.
        '''
        if self.timer:
            self.timer.cancel()
            self.timer = None
        self.timer = reactor.callLater(timeout, fn, *args, **kw)



################################################################
#
#  TESTING
#
################################################################
if __name__ == "__main__":
    from twisted.python.log import startLogging
    startLogging(sys.stdout)

    reactor.run()

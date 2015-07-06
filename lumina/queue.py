#-*- python -*-
from twisted.internet.defer import Deferred
from twisted.internet import reactor

# Possible improvements:
#   - Queue(serial=True) to support serial execution. get_next() returns None
#     when there is an active transmission
#   - Queue(serial=False) to support concurrent execute. get_next() will always
#     return the next object. This requires to move the timeout functionality
#     into the queue request object.


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


    def callback(self, data):
        ''' Call response callback of the active queued request. The active
            request will be removed
        '''
        if self.timer and self.timer.active():
            self.timer.cancel()
            self.timer = None
        (request, self.active) = (self.active, None)
        request['defer'].callback(data)



    def errback(self, reason):
        ''' Send failed response to the caller of the request. The active
            request will be removed.
        '''
        if self.timer and self.timer.active():
            self.timer.cancel()
            self.timer = None
        (request, self.active) = (self.active, None)
        request['defer'].errback(reason)



    def set_timeout(self, timeout, fn, *args, **kw):
        ''' Set a timeout and callback. Calling callback() or errback() will cancel
            the timeout.
        '''
        if self.timer and self.timer.active():
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

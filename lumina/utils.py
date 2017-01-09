#-*- python -*-
#from __future__ import absolute_import

from twisted.internet import reactor


def add_defer_timeout(defer, timeout, fn, *args, **kw):
    ''' Add a timeout to the defer object and return the timer. It will call fn(*args,**kw) on
        timeout. The timer will be cleaned up automatically, both if the timer times out, or if
        the deferred object is fired by other cases.
    '''

    timer = reactor.callLater(timeout, fn, *args, **kw)

    def timeout_cancel(result):
        ''' Stop the timer if it has not been fired '''
        if timer.active():
            timer.cancel()
        return result

    defer.addBoth(timeout_cancel)

    return timer


def cmp_dict(a,b,l):
    ''' Compare dict a with dict b using keys from l. Return True if all elements are
        either equal (using !=) or if element is not present in either a or b.
        '''
    for i in l:
        ia=i in a
        ib=i in b
        if ia != ib or (ia and ib and a[i] != b[i]):
            return False
    return True

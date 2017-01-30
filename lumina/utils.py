# -*- python -*-
from __future__ import absolute_import

from twisted.internet import reactor


def add_defer_timeout(defer, timeout, callback, *args, **kw):
    ''' Add a timeout to the defer object and return the timer. It will call callback(*args,**kw)
        on timeout. The timer will be cleaned up automatically, both if the timer times out, or
        if the deferred object is fired by other cases.
    '''

    timer = reactor.callLater(timeout, callback, *args, **kw)

    def timeout_cancel(result):
        ''' Stop the timer if it has not been fired '''
        if timer.active():
            timer.cancel()
        return result

    defer.addBoth(timeout_cancel)

    return timer


def cmp_dict(a, b, c):
    ''' Compare dict a with dict b using keys from c. Return True if all elements are
        either equal (using !=) or if element is not present in either a or b.
        '''
    for i in c:
        ina = i in a
        inb = i in b
        if ina != inb or (ina and inb and a[i] != b[i]):
            return False
    return True


def listify_dict(obj):
    ''' Return a list with 'k=v' elements from obj '''
    return ['%s=%s' %(k, str_object(v, max_elements=0)) for k, v in obj.items()]


def str_object(obj, max_elements=0, brackets=True):
    ''' Return a string representation of obj. '''

    # max_elements=0: [..#34..]
    # max_elements=5: [1,2,3,4,5 ... +3 more]

    if isinstance(obj, list):
        delim = ('[', ']')
        obj = [str_object(v, max_elements=0) for v in obj]

    elif isinstance(obj, tuple):
        delim = ('(', ')')
        obj = [str_object(v, max_elements=0) for v in obj]

    elif isinstance(obj, dict):
        delim = ('{', '}')
        obj = listify_dict(obj)

    else:
        return str(obj)

    if not brackets:
        delim = ('', '')

    if len(obj) > max_elements:
        if max_elements == 0:
            return delim[0] + '..#' + str(len(obj)) + '..' + delim[1]
        else:
            more = len(obj)-max_elements
            obj = obj[:max_elements]
            obj.append(' ... +%s more' %(more))
            # fallthrough

    return delim[0] + ','.join(obj) + delim[1]

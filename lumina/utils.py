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


def cmp_dict(a, b, l):
    ''' Compare dict a with dict b using keys from l. Return True if all elements are
        either equal (using !=) or if element is not present in either a or b.
        '''
    for i in l:
        ina = i in a
        inb = i in b
        if ina != inb or (ina and inb and a[i] != b[i]):
            return False
    return True


def listify_dict(object, max_elements=0):
    ''' Return a list with 'k=v' elements from object '''
    return ['%s=%s' %(k, str_object(v, max_elements=0)) for k, v in object.items()]


def str_object(object, max_elements=0, brackets=True):
    ''' Return a string representation of object. '''

    # max_elements=0: [..#34..]
    # max_elements=5: [1,2,3,4,5 ... +3 more]

    if isinstance(object, list):
        delim = ('[', ']')
        object = [str_object(v, max_elements=0) for v in object]

    elif isinstance(object, tuple):
        delim = ('(', ')')
        object = [str_object(v, max_elements=0) for v in object]

    elif isinstance(object, dict):
        delim = ('{', '}')
        object = listify_dict(object)

    else:
        return str(object)

    if not brackets:
        delim = ('', '')

    if len(object) > max_elements:
        if max_elements == 0:
            return delim[0] + '..#' + str(len(object)) + '..' + delim[1]
        else:
            more = len(object)-max_elements
            object = object[:max_elements]
            object.append(' ... +%s more' %(more))
            # fallthrough

    return delim[0] + ','.join(object) + delim[1]

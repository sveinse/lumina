# -*- python -*-
from __future__ import absolute_import

from twisted.internet import reactor
from twisted.internet.protocol import Factory


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


def connectEndpoint(protocol, endpoint, *args, **kw):
    ''' A clone of twisted.internet.endpoint.connectEndpoint(), where this both 
        creates the endpoint(*args, **kw) and sets up a non-noisy factory.
    '''
    class OneShotFactory(Factory):
        noisy = False
        def buildProtocol(self, addr):
            return protocol

    ep = endpoint(reactor, *args, **kw)
    return ep.connect(OneShotFactory())


# Written by Stephen McDonald, copied from
# http://blog.jupo.org/2012/04/06/topological-sorting-acyclic-directed-graphs/
def topolgical_sort(graph):
    """
    Repeatedly go through all of the nodes in the graph, moving each of
    the nodes that has all its edges resolved, onto a sequence that
    forms our sorted graph. A node has all of its edges resolved and
    can be moved once all the nodes its edges point to, have been moved
    from the unsorted graph onto the sorted one.
    """

    # This is the list we'll return, that stores each node
    # in topological order.
    sequence = []

    # Convert the unsorted graph into a hash table. This gives us
    # constant-time lookup for checking if edges are unresolved, and
    # for removing nodes from the unsorted graph.
    graph = dict(graph)

    # Run until the unsorted graph is empty.
    while graph:

        # Go through each of the node/edges pairs in the unsorted
        # graph. If a set of edges doesn't contain any nodes that
        # haven't been resolved, that is, that are still in the
        # unsorted graph, remove the pair from the unsorted graph,
        # and append it to the sorted graph. Note here that by using
        # using the items() method for iterating, a copy of the
        # unsorted graph is used, allowing us to modify the unsorted
        # graph as we move through it. We also keep a flag for
        # checking that that graph is acyclic, which is true if any
        # nodes are resolved during each pass through the graph. If
        # not, we need to bail out as the graph therefore can't be
        # sorted.
        acyclic = False
        for node, edges in list(graph.items()):
            for edge in edges:
                if edge in graph:
                    break
            else:
                acyclic = True
                del graph[node]
                sequence.append(node)

        if not acyclic:
            # Uh oh, we've passed through all the unsorted nodes and
            # weren't able to resolve any of them, which means there
            # are nodes with cyclic edges that will never be resolved,
            # so we bail out with an error.
            raise RuntimeError("A cyclic dependency occurred")

    return sequence
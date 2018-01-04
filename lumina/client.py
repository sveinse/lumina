# -*- python -*-
""" Client interface """
from __future__ import absolute_import

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.endpoints import TCP4ClientEndpoint #, connectProtocol

from lumina.log import Logger
from lumina.protocol import LuminaProtocol
from lumina.utils import connectProtocol



class Client(object):
    ''' A simple one-shot Client interface to connect to the Lumina server '''

    def __init__(self, host='127.0.0.1', port=5326):
        ''' Initalize the client '''
        self.log = Logger(namespace='client')
        self.serverhost = host
        self.serverport = port

    def send(self, message):
        ''' Send a single message '''
        defer = Deferred()
        endpoint = TCP4ClientEndpoint(reactor, self.serverhost, self.serverport)
        self.protocol = LuminaProtocol(self)
        d = connectProtocol(endpoint, self.protocol)

        def ok(result):
            result.send(message).chainDeferred(defer)
        def err(failure):
            defer.errback(failure)
            
        d.addCallback(ok)
        d.addErrback(err)

        return defer

# -*- python -*-
""" Lumina client plugin """
from __future__ import absolute_import, division, print_function

from twisted.internet.defer import Deferred
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol

from lumina.plugin import Plugin
from lumina.protocol import LuminaProtocol
from lumina.message import Message


class Client(Plugin):
    ''' Lumina client
    '''

    def setup(self):
        self.server = self.master.config.get('server')
        self.port = self.master.config.get('port')


    def send(self, message):
        ''' Send a single message '''
        defer = Deferred()
        endpoint = TCP4ClientEndpoint(self.master.reactor, self.server, self.port)
        self.protocol = LuminaProtocol(self)
        d = connectProtocol(endpoint, self.protocol)

        def ok(result):
            result.send(message).chainDeferred(defer)
        def err(failure):
            defer.errback(failure)
            
        d.addCallback(ok)
        d.addErrback(err)

        return defer


PLUGIN = Client
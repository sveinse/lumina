# -*- python -*-
""" Generic implementation of a reconnecting class """
from __future__ import absolute_import, division, print_function

import random

from lumina.log import Logger



# Inspired by twisted ReconnectingClientFactory,
# http://twistedmatrix.com/documents/current/api/twisted.internet.protocol.ReconnectingClientFactory.html
class Reconnector(object):
    ''' A class for attempting reconnects, handling exponential timeout delays
        when the connection fails.
    '''
    noisy = True
    log = Logger()

    maxDelay = 3600
    initialDelay = 1.0
    factor = 2.7182818284590451
    # factor = 1.6180339887498948
    jitter = 0.11962656472
    delay = initialDelay
    retries = 0
    maxRetries = None
    _callID = None
    continueTrying = 1


    def __init__(self, reactor):
        self.reactor = reactor


    def connect(self):
        """
        Called by reconnector when a new connection should be attempted.
        """
        pass


    def retry(self):
        """
        Have this class connect again, after a suitable delay.
        """
        if not self.continueTrying:
            if self.noisy:
                self.log.info("Abandoning reconnect on explicit request")
            return

        self.retries += 1
        if self.maxRetries is not None and (self.retries > self.maxRetries):
            if self.noisy:
                self.log.info("Abandoning reconnect after {r} retries.",
                              r=self.retries)
            return

        self.delay = min(self.delay * self.factor, self.maxDelay)
        if self.jitter:
            self.delay = random.normalvariate(self.delay,
                                              self.delay * self.jitter)

        if self.noisy:
            self.log.info("Will retry reconnect in {d} seconds",
                          d=self.delay)

        def reconnector():
            self._callID = None
            self.connect()
        self._callID = self.reactor.callLater(self.delay, reconnector)


    def stopTrying(self):
        """
        Put a stop to any attempt to reconnect in progress.
        """
        if self._callID:
            self._callID.cancel()
            self._callID = None
        self.continueTrying = 0


    def resetDelay(self):
        """
        Call this method after a successful connection: it resets the delay and
        the retry counter.
        """
        self.delay = self.initialDelay
        self.retries = 0
        self._callID = None
        self.continueTrying = 1

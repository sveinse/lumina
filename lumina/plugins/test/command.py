# -*- python -*-
from __future__ import absolute_import

from twisted.internet import reactor
from twisted.internet.defer import Deferred

from lumina.node import Node


class Command(Node):
    """ (TEST) A plugin for testing commands """

    # --- Interfaces
    def configure(self, master):

        self.events = (
            'event',
        )

        self.commands = {
            '1' :        lambda a: 1,
            '2' :        lambda a: 2,
            '3' :        lambda a: 3,
            'none':      lambda a: None,
            'true':      lambda a: True,
            'false':     lambda a: False,
            'echo':      lambda a: a.args,
            'delay':     lambda a: self.delay(2, 42),
            'never':     lambda a: Deferred(),
            'exception': lambda a: self.exc(),
            'error':     lambda a: self.err(),
            'event':     lambda a: self.delay_event(2, 43),
        }

    def setup(self, master):
        Node.setup(self, master)
        self.status.set_GREEN()

    def delay(self, time, value):
        defer = Deferred()
        def delay_done(value):
            defer.callback(value)
        reactor.callLater(int(time), delay_done, value)
        return defer

    def delay_event(self, time, value):
        def delay_done(value):
            self.sendEvent('event', value)
        reactor.callLater(int(time), delay_done, value)
        return True

    def exc(self):
        raise Exception("Test Exception")

    def err(self):
        return self.nonexist


PLUGIN = Command

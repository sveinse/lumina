# -*- python -*-
from __future__ import absolute_import

from twisted.internet.task import LoopingCall
from twisted.internet.defer import Deferred
from twisted.internet import reactor

from lumina.node import Node



class Test(Node):
    ''' Test node '''

    CONFIG = {
        'test': dict(default=0, help='Test help', type=int),
    }


    # --- Interfaces
    def configure(self, main):

        self.events = [
            'timer1',
            'timer2',

            # For testing echo
            'zero',
            'one',
            'two',
            'fail',
            'unknown'
        ]

        self.commands = {
            'log'       : lambda a: self.log.info('Logging: {a}', a=a),
            'true'      : lambda a: True,
            '1'         : lambda a: 1,
            '2'         : lambda a: 2,
            '3'         : lambda a: 3,
            'list'      : lambda a: (1, 2, 3),
            'delay'     : lambda a: self.delay(a.args[0], (1, 2, 3)),
            'fail'      : lambda a: self.err(),
            'never'     : lambda a: Deferred(),
            'echo'      : lambda a: self.emit(a.args[0]),
        }


    # --- Initialization
    def __init__(self):
        self.count = 0

    def setup(self, main):
        Node.setup(self, main)

        self.status.set_GREEN()

        self.loop1 = LoopingCall(self.loop_cb1)
        self.loop1.start(10, False)

        self.loop2 = LoopingCall(self.loop_cb2)
        self.loop2.start(12, False)


    # --- Worker
    def loop_cb1(self):
        self.count += 1
        self.emit('timer1', self.count)

    def loop_cb2(self):
        self.count += 1
        self.emit('timer2', self.count)

    def delay(self, time, data):
        defer = Deferred()
        reactor.callLater(int(time), self.done, defer, data)
        return defer

    def done(self, defer, data):
        defer.callback(data)

    def err(self):
        raise Exception("Failed")



# Main plugin object class
PLUGIN = Test

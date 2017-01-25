# -*- python -*-
from __future__ import absolute_import

from twisted.internet.task import LoopingCall
from twisted.internet.defer import Deferred
from twisted.internet import reactor

from lumina.node import Node
from lumina.callback import Callback



class Test(Node):
    ''' Test node '''
    name = 'TEST'

    # --- Interfaces
    def configure(self):
        self.events = [
            'timer',

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
        self.cbevent = Callback()
        self.count = 0

    def setup(self, main):
        Node.setup(self, main)
        self.status.set_GREEN()
        self.loop = LoopingCall(self.loop_cb)
        self.loop.start(20, False)


    # --- Worker
    def loop_cb(self):
        self.count += 1
        self.emit('timer', self.count)

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

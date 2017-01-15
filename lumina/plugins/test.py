# -*- python -*-
from __future__ import absolute_import

from twisted.python import log
from twisted.internet.task import LoopingCall
from twisted.internet.defer import Deferred
from twisted.internet import reactor

from lumina.leaf import Leaf
from lumina.event import Event
from lumina.callback import Callback



class Test(Leaf):
    name = 'TEST'

    # --- Interfaces
    def configure(self):
        self.events = [
            'timer',
        ]

        self.commands = {
            'log'       : lambda a : self.log.info('Logging: {a}', a=a),
            'true'      : lambda a : True,
            '1'         : lambda a : 1,
            '2'         : lambda a : 2,
            '3'         : lambda a : 3,
            'list'      : lambda a : (1,2,3),
            'delay'     : lambda a : self.delay(2,(1,2,3)),
            'fail'      : lambda a : self.err(),
            'never'     : lambda a : Deferred(),
        }


    # --- Initialization
    def __init__(self):
        self.configure()
        self.cbevent = Callback()
        self.n = 0

    def setup(self, main):
        Leaf.setup(self, main)
        self.loop = LoopingCall(self.loop_cb)
        self.loop.start(20, False)


    # --- Worker
    def loop_cb(self):
        self.n = self.n+1
        self.send(Event('timer',self.n))

    def delay(self,time,data):
        d = Deferred()
        reactor.callLater(int(time),self.done,d,data)
        return d

    def done(self,d,data):
        d.callback(data)

    def err(self):
        raise Exception("Failed")



# Main plugin object class
PLUGIN = Test

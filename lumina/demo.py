from twisted.python import log
from callback import Callback
from twisted.internet.task import LoopingCall
from twisted.internet.defer import Deferred
from twisted.internet import reactor

from endpoint import Endpoint
from core import Event


class Demo(Endpoint):

    # --- Interfaces
    def get_events(self):
        return [
            'timer',
        ]

    def get_actions(self):
        return {
            'immediate' : lambda a : Event('imme',3,4,5),
            'delay'     : lambda a : self.delay(2,Event().parse('delay{1,2,3}')),
            'fail1'     : lambda a : Exception("Failed"),
            'fail2'     : lambda a : self.err(),
            'fail3'     : lambda a : self.delay(2,Exception("Failed")),
        }


    # --- Initialization
    def __init__(self):
        self.cbevent = Callback()
        self.n = 0

    def setup(self):
        self.loop = LoopingCall(self.loop_cb)
        #self.loop.start(20, False)


    # --- Worker
    def loop_cb(self):
        self.n = self.n+1
        self.event('timer',self.n)

    def delay(self,time,data):
        self.d = Deferred()
        reactor.callLater(int(time),self.done,data)
        return self.d

    def done(self,data):
        self.d.callback(data)

    def err(self):
        raise Exception("Failed")

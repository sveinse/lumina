from twisted.python import log
from callback import Callback
from twisted.internet.task import LoopingCall
from core import Event
from twisted.internet.defer import Deferred
from twisted.internet import reactor



class Demo(object):

    def __init__(self):
        self.cbevent = Callback()

    def setup(self):
        self.loop = LoopingCall(self.loop_cb)
        #self.loop.start(20, False)

    # -- Event handler
    def add_eventcallback(self, callback, *args, **kw):
        self.cbevent.addCallback(callback, *args, **kw)
    def event(self,event,*args):
        self.cbevent.callback(Event(event,*args))

    # -- List of supported event and actions
    def get_events(self):
        return [ 'a', 'b', 'c', 'test' ]

    def get_actions(self):
        return {
            'x' : lambda a : log.msg("X run"),
            'y' : lambda a : self.delay(Event('y{1,2,3}')),
            'y2' : lambda a : self.delay('y2'),
            'z' : lambda a : log.msg("Z run"),
            'w' : lambda a : 'abcd',
        }

    # -- Worker
    def loop_cb(self):
        self.event('a')

    def delay(self,data):
        self.d = Deferred()
        reactor.callLater(2,self.done,data)
        return self.d

    def done(self,data):
        self.d.callback(data)


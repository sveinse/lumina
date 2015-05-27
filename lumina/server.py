# -*-python-*-
import os,sys

from twisted.internet import reactor
from twisted.python import log
#from twisted.internet.protocol import ClientFactory, Protocol
#from twisted.internet.defer import Deferred

from callback import Callback
from core import Event


class Server(object):

    def __init__(self,port):
        self.port = port
        self.cbevent = Callback()

    def setup(self):
        pass

    def close(self):
        pass

    # -- Event handler
    def add_eventcallback(self, callback, *args, **kw):
        self.cbevent.addCallback(callback, *args, **kw)
    def _event(self,event,*args):
        self.cbevent.callback(Event(event,*args))

    def get_events(self):
        return [ ]

    def get_actions(self):
        return { }



################################################################
#
#  TESTING
#
################################################################
if __name__ == "__main__":
    from twisted.python.log import startLogging
    startLogging(sys.stdout)

    def error(reason,td):
        log.msg("ERROR",reason)
        reactor.stop()

    def ready(result,td):
        log.msg("READY",result)
        #d = td.turnOn(1)
        #d = td.turnOn(2)
        #d = td.turnOn(3)

    def event(result,td):
        log.msg("EVENT",result)

    td = Telldus()
    d = td.setup()
    td.addCallbackReady(ready,td)
    td.addCallbackError(error,td)
    td.addCallbackEvent(event,td)
    d = td.turnOn(1)
    d = td.turnOn(2)
    d = td.turnOn(3)

    reactor.run()

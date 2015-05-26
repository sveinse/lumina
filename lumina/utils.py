# -*-python-*-
import os,sys
from twisted.internet import reactor
from twisted.python import log
from twisted.internet.defer import Deferred

from callback import Callback
from core import Event


class Utils(object):

    def __init__(self):
        self.cbevent = Callback()

    def setup(self):
        reactor.addSystemEventTrigger('before','shutdown',self._event,'stopping')
        reactor.callWhenRunning(self._event,'starting')

    def close(self):
        pass


    # --- Event handler
    def _event(self,event,*args):
        self.cbevent.callback(Event(event,*args))
    def add_eventcallback(self, callback, *args, **kw):
        self.cbevent.addCallback(callback, *args, **kw)


    # --- Actions
    def delay(self,delay):
        d = Deferred()
        reactor.callLater(int(delay), d.callback, None)
        return d

    def stop(self):
        log.msg("SERVER STOPPING", system="MAIN")
        self._event('stopping')
        # This location is not perfect, as any deferred objects in the stopping event above
        # will not be executed before the reactor is stopped
        reactor.stop()

    def log(self,*args,**kw):
        log.msg("LOG %s %s" %(args,kw), system="MAIN")


    # --- Get list of events and actions
    def get_events(self):
        return [ 'starting', 'stopping' ]

    def get_actions(self):
        return {
            'delay' : lambda a : self.delay(a.args[0]),
            'stop'  : lambda a : self.stop(),
            'log'   : lambda a : self.log(*a.args,**a.kw),
        }

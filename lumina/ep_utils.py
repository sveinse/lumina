# -*-python-*-
import os,sys
from twisted.internet import reactor
from twisted.python import log
from twisted.internet.defer import Deferred

from endpoint import Endpoint


class Utils(Endpoint):
    system = 'UTIL'

    # --- Interfaces
    def register(self):
        self.events = [
            'starting',
            'stopping'
        ]

        self.commands = {
            'delay' : lambda a : self.delay(a.args[0]),
            'stop'  : lambda a : self.stop(),
            'log'   : lambda a : self.log(*a.args,**a.kw),
        }


    # --- Initialization
    def setup(self):
        reactor.addSystemEventTrigger('before','shutdown',self.event,'stopping')
        reactor.callWhenRunning(self.event,'starting')


    # --- Actions
    def delay(self,delay):
        d = Deferred()
        reactor.callLater(int(delay), d.callback, None)
        return d

    def stop(self):
        log.msg("SERVER STOPPING", system=self.system)
        self.event('stopping')
        # This location is not perfect, as any deferred objects in the stopping event above
        # will not be executed before the reactor is stopped
        reactor.stop()

    def log(self,*args,**kw):
        log.msg("LOG %s %s" %(args,kw), system=self.system)

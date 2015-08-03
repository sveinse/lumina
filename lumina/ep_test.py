# -*-python-*-
import os,sys
from twisted.python import log
from twisted.internet.defer import Deferred
from twisted.internet import reactor

from endpoint import Endpoint
from event import Event as E
from exceptions import *

class Test(Endpoint):
    system = 'TEST'
    name = 'TEST'

    # --- Interfaces
    def configure(self):
        self.events = [ ]

        recycle = E('t/recycle')
        self.commands = {
            # Fails with nothing to run
            't/empty'  : ( ),
            't/null'   : None,

            # Basic command support
            't/none'   : lambda a : None,
            't/true'   : lambda a : True,
            't/false'  : lambda a : False,
            't/list'   : lambda a : ( True, False),

            't/log'    : lambda a : self.log(a),
            't/args'   : ( 't/log{1,2,3}', 't/log{42,sure=yes}' ),
            't/arg3'   : ( lambda a : ( E('t/log',1,3,a.args[0]), ), ),

            # Aliases
            't/alias'     : ( 't/true', ),
            't/alias2'    : ( 't/true', 't/null', 't/empty', 't/nonexist' ),
            't/aliaserr'  : ( 't/nonexist', ),
            't/aliaserr2' : ( 't/true', 't/nonexist', ),

            # It should catch these
            't/loop'   : ( 't/loop', ),
            't/loop1'  : ( 't/loop2', ),
            't/loop2'  : ( 't/loop1', ),
            't/loopx'  : ( lambda a : ( 't/loopy', ), ),
            't/loopy'  : ( lambda a : ( 't/loopx', ), ),

            # Composite ok and failure objects
            't/ok'     : lambda a : True,
            't/ok3'    : ( 't/ok', 't/ok', 't/ok' ),

            # Failure and failure composites
            't/fail'   : lambda a : self.fail(),
            't/fail1'  : ( 't/ok', 't/fail', 't/ok' ),
            't/fail3'  : ( 't/fail', 't/fail', 't/fail' ),

            # Test timeout
            't/forever'  : lambda a : self.forever(),
            't/forever2' : ( 't/forever', 't/forever' ),

            # Reuse objects (called twice should not be dangerous)
            't/reuse'  : ( recycle, ),

            # Delays
            't/delay'  : lambda a : self.delay(a.args[0]),
            't/delay2' : ( 't/delay{3}', 't/delay{2}' , 't/delay{1}' ),
        }


    # --- Initialization
    def __init__(self):
        self.state = 'init'


    # --- Commands
    def fail(self):
        raise CommandException('Failed')
    def forever(self):
        return Deferred()
    def delay(self,time,data=None):
        log.msg("HERE")
        d = Deferred()
        reactor.callLater(int(time),self._done,d)
        return d
    def _done(self,d):
        log.msg("DONE")
        d.callback(True)
    def log(self,a):
        log.msg("Log: %s" %(a,))

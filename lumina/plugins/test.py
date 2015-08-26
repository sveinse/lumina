# -*-python-*-
import os,sys
from twisted.python import log
from twisted.internet.defer import Deferred
from twisted.internet import reactor

from ..endpoint import Endpoint
from ..event import Event as E
from ..exceptions import *



class Test(Endpoint):
    system = 'TEST'
    name = 'TEST'

    # --- Interfaces
    def configure(self):
        self.events = [ ]

        recycle = E('r/recycle')

        commands = {
            # Fails with nothing to run
            '/empty'   : ( ),
            '/null'    : None,

            # Basic command support
            '/none'    : lambda a : None,
            '/true'    : lambda a : True,
            '/false'   : lambda a : False,
            '/list'    : lambda a : ( True, False),

            # Argument testing
            '/log'     : lambda a : self.log(a),
            '/arg'     : lambda a : self.delay(a.args[0]),
            '/arg2'    : ( lambda a : E('r/arg',a.args[0]), ),
            '/args'    : ( 'r/log{1,2,3}', 'r/log{42,sure=yes}' ),
            '/arg3'    : ( lambda a : ( E('r/log',1,3,a.args[0]), ), ),

            # Aliases
            '/alias'     : ( 'r/true', ),
            '/alias2'    : ( 'r/true', 'r/null', 'r/empty', 'r/nonexist' ),
            '/aliaserr'  : ( 'r/nonexist', ),
            '/aliaserr2' : ( 'r/true', 'r/nonexist', ),

            # It should catch these
            '/loop'   : ( 'r/loop', ),
            '/loop1'  : ( 'r/loop2', ),
            '/loop2'  : ( 'r/loop1', ),
            '/loopx'  : ( lambda a : ( 'r/loopy', ), ),
            '/loopy'  : ( lambda a : ( 'r/loopx', ), ),

            # Composite ok and failure objects
            '/ok'     : lambda a : True,
            '/ok3'    : ( 'r/ok', 'r/ok', 'r/ok' ),
            '/fail1'  : ( 'r/ok', 'r/fail', 'r/ok' ),
            '/fail2'  : ( 'r/ok', 'r/arg', 'r/ok' ),
            '/fail3'  : ( 'r/fail', 'r/fail', 'r/fail' ),

            # Failure and failure composites
            '/fail'    : lambda a : self.fail(),

            # Test timeout
            '/forever'  : lambda a : self.forever(),
            '/forever2' : ( 'r/forever', 'r/forever' ),

            # Reuse objects (called twice should not be dangerous)
            '/reuse'   : ( recycle, ),

            # Delays
            '/delay'   : lambda a : self.delay(a.args[0]),
            '/delay2'  : ( 'r/delay{3}', 'r/delay{2}' , 'r/delay{1}' ),
        }
        prefix = self.prefix
        self.commands = {}
        for (cmd,data) in commands.items():
            if prefix == 'r' and not callable(data):
                continue
            self.commands[prefix + cmd] = data


    # --- Initialization
    def __init__(self,prefix='r'):
        self.state = 'init'
        self.prefix = prefix


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



# Main plugin object class
PLUGIN = Test

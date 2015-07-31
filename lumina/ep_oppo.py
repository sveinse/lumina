# -*-python-*-
import os,sys
from twisted.internet import reactor
from twisted.python import log
from twisted.internet.protocol import Protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet.serialport import SerialPort, EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from serial.serialutil import SerialException

from endpoint import Endpoint
from queue import Queue
from exceptions import *


def ison(result):
    if result[0]=='ON':
        return True
    else:
        return False


class OppoProtocol(LineReceiver):
    delimiter = '\x0d'
    timeout = 10
    system = 'OPPO'

    def __init__(self,parent):
        self.state = 'init'
        self.parent = parent
        self.queue = Queue()


    def setstate(self,state):
        (old, self.state) = (self.state, state)
        if state != old:
            log.msg("STATE change: '%s' --> '%s'" %(old,state), system=self.system)


    def connectionMade(self):
        self.setstate('connected')
        self.parent.event('oppo/connected')

        # Send a ping command to make the state machine progress
        d=self.command('QPW')
        d.addErrback(lambda a : None)


    def connectionLost(self,reason):
        self.setstate('closed')
        self.parent.event('oppo/disconnected',reason.getErrorMessage())


    def lineReceived(self, data):
        log.msg("RAW  >>>  (%s)'%s'" %(len(data),data), system=self.system)

        # Oppo has three incoming message formats:
        #    Short reply:    @(OK|ER) [ARG1 [...]]
        #    Verbose reply:  @CMD (OK|ER) [ARG1 [...]]
        #    Status update:  @CMD [ARG1 [...]]

        # Parse line (skip any chars before '@', but not allow any more after it)
        if '@' not in data:
            log.msg("Frame error, ignoring junk ('%s')" %(data,), system=self.system)
            return
        data = data[data.find('@'):]
        if '@' in data[1:]:
            log.msg("Frame error, illegal chars ('%s')" %(data,), system=self.system)
            return
        if len(data) > 25:
            log.msg("Frame error, line too long ('%s')" %(data,), system=self.system)
            return

        # Split line by spaces. args will be at least one element long
        args = data[1:].split(' ')

        # Log command, but omit logging certain verbose events
        #if args[0] not in ('UTC', ):
        #    log.msg("RAW  >>>  (%s)'%s'" %(len(data),data), system=self.system)

        # Short message format? Implies a reply type by design. Make it into a verbose reply
        if args[0] in ('OK', 'ER'):
            if not self.queue.active:
                log.msg("Protocol error. Reply to unknown command ('%s')" %(data,),
                        system=self.system)
                return
            args.insert(0,self.queue.active['command'])

        # Extract command
        cmd = args.pop(0)
        if len(cmd) != 3:
            log.msg("Protocol error, invalid length on command ('%s')" %(data,),
                    system=self.system)
            return

        # From here on, consider this a valid frame and thus an active connection
        self.setstate('active')

        # Reply type (verbose and short), which is given by the second argument being OK|ER
        if len(args)>0 and args[0] in ('OK', 'ER'):
            result = args.pop(0)

            if self.queue.active is None or cmd != self.queue.active['command']:
                log.msg("Protocol error, unknown command in reply ('%s')" %(data,),
                        system=self.system)
                return

            # Send reply back to caller
            if result == 'OK':
                self.queue.callback(args)
            else:
                self.queue.errback(CommandFailedException(args[0]))
            self.send_next()
            return

        # Status update message we're interested in?
        for (ev,d) in self.parent.events.items():

            # Don't consider events that does not have a payload
            if d is None:
                continue

            # Consider only response types in the events list
            if d['cmd'] != cmd:
                continue
            if d['arg']:
                if len(args)==0 or d['arg'] != args[0]:
                    continue

            # Pass on to factory to handle the event
            self.parent.event(ev,*args)
            return

        # Not interested in the received message
        log.msg("-IGNORED-", system=self.system)


    def command(self, command, *args):
        if self.state in ('error', 'closed'):
            raise NotConnectedException()
        a = ' '.join(args)
        if a:
            a = ' ' + a
        data='#%s%s' %(command,a)

        d = self.queue.add(data=data, command=command)
        self.send_next()
        return d


    def send_next(self):
        if self.state not in ('connected', 'active', 'inactive'):
            return

        # Send data
        if self.queue.get_next() is not None:
            data = self.queue.active['data']
            log.msg("RAW  <<<  (%s)'%s'" %(len(data),data), system=self.system)
            self.transport.write(data.encode('ascii')+self.delimiter)

            # Set timeout
            self.queue.set_timeout(self.timeout, self.timedout)


    def timedout(self):
        # The timeout response is to fail the request and proceed with the next command
        log.msg("Command '%s' timed out" %(self.queue.active['command'],), system=self.system)
        self.setstate('inactive')
        self.queue.errback(TimeoutException())
        self.send_next()



class Oppo(Endpoint):
    system = 'OPPO'
    name = 'OPPO'

    # --- Interfaces
    def configure(self):
        self.events = {
            'oppo/starting'     : None,  # Created oppo object
            'oppo/stopping'     : None,  # close() have been called
            'oppo/connected'    : None,  # Connection with Oppo has been made
            'oppo/disconnected' : None,  # Lost connection with Oppo
            'oppo/error'        : None,  # Connection failed

            'oppo/off'     : dict(cmd='UPW', arg='0'),
            'oppo/on'      : dict(cmd='UPW', arg='1'),
            'oppo/play'    : dict(cmd='UPL', arg='PLAY'),
            'oppo/pause'   : dict(cmd='UPL', arg='PAUS'),
            'oppo/stop'    : dict(cmd='UPL', arg='STOP'),
            'oppo/home'    : dict(cmd='UPL', arg='HOME'),
            'oppo/nodisc'  : dict(cmd='UPL', arg='DISC'),
            'oppo/loading' : dict(cmd='UPL', arg='LOAD'),
            'oppo/closing' : dict(cmd='UPL', arg='CLOS'),
            'oppo/audio'   : dict(cmd='UAT', arg=None),
        }

        self.commands = {
            'oppo/state'   : lambda a : self.protocol.state,
            'oppo/raw'     : lambda a : self.c(*a.args),

            'oppo/ison'    : lambda a : self.c('QPW').addCallback(ison),

            'oppo/play'    : lambda a : self.c('PLA'),
            'oppo/pause'   : lambda a : self.c('PAU'),
            'oppo/stop'    : lambda a : self.c('STP'),
            'oppo/on'      : lambda a : self.c('PON'),
            'oppo/off'     : lambda a : self.c('POF'),
            'oppo/verbose' : lambda a : self.c('SVM','2'),
        }


    # --- Initialization
    def __init__(self, port):
        self.port = port
        self.sp = None

    def setup(self):
        self.protocol = OppoProtocol(self)
        try:
            self.protocol.setstate('starting')
            self.sp = SerialPort(self.protocol, self.port, reactor,
                                 baudrate=9600,
                                 bytesize=EIGHTBITS,
                                 parity=PARITY_NONE,
                                 stopbits=STOPBITS_ONE,
                                 xonxoff=0,
                                 rtscts=0)
            self.event('oppo/starting')
        except SerialException as e:
            log.err(system=self.system)
            self.protocol.setstate('error')
            self.event('oppo/error',e.message)

    def close(self):
        self.event('oppo/stopping')
        if self.sp:
            self.sp.loseConnection()


    # --- Convenience
    def c(self,*args,**kw):
        return self.protocol.command(*args,**kw)


    # --- Commands

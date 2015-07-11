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


class OppoException(Exception):
    pass
class CommandFailedException(OppoException):
    pass
class NotConnectedException(OppoException):
    pass
class TimeoutException(OppoException):
    pass


# Translation from Oppo commands to event commands
eventlist = (
    dict(name='oppo/off',      cmd='UPW', arg='0'),
    dict(name='oppo/on',       cmd='UPW', arg='1'),
    dict(name='oppo/play',     cmd='UPL', arg='PLAY'),
    dict(name='oppo/pause',    cmd='UPL', arg='PAUS'),
    dict(name='oppo/stop',     cmd='UPL', arg='STOP'),
    dict(name='oppo/home',     cmd='UPL', arg='HOME'),
    dict(name='oppo/nodisc',   cmd='UPL', arg='DISC'),
    dict(name='oppo/loading',  cmd='UPL', arg='LOAD'),
    dict(name='oppo/closing',  cmd='UPL', arg='CLOS'),
    dict(name='oppo/audio',    cmd='UAT', arg=None),
)


class OppoProtocol(LineReceiver):
    delimiter = '\x0d'
    timeout = 10

    def __init__(self,parent):
        self.state = 'init'
        self.parent = parent
        self.queue = Queue()


    def setstate(self,state):
        (old, self.state) = (self.state, state)
        if state != old:
            log.msg("STATE change: '%s' --> '%s'" %(old,state), system='OPPO')


    def connectionMade(self):
        self.setstate('connected')
        self.parent.event('oppo/connected')

        # Send a ping command to make the state machine progress
        d=self.command('QPW')
        d.addErrback(lambda a : None)


    def connectionLost(self,reason):
        self.setstate('closed')
        self.parent.event('oppo/disconnected',reason)


    def lineReceived(self, data):
        log.msg("RAW  >>>  (%s)'%s'" %(len(data),data), system='OPPO')

        # Oppo has three incoming message formats:
        #    Short reply:    @(OK|ER) [ARG1 [...]]
        #    Verbose reply:  @CMD (OK|ER) [ARG1 [...]]
        #    Status update:  @CMD [ARG1 [...]]

        # Parse line (skip any chars before '@', but not allow any more after it)
        if '@' not in data:
            log.msg("Frame error, ignoring junk ('%s')" %(data,), system='OPPO')
            return
        data = data[data.find('@'):]
        if '@' in data[1:]:
            log.msg("Frame error, illegal chars ('%s')" %(data,), system='OPPO')
            return
        if len(data) > 25:
            log.msg("Frame error, line too long ('%s')" %(data,), system='OPPO')
            return

        # Split line by spaces. args will be at least one element long
        args = data[1:].split(' ')

        # Log command, but omit logging certain verbose events
        #if args[0] not in ('UTC', ):
        #    log.msg("RAW  >>>  (%s)'%s'" %(len(data),data), system='OPPO')

        # Short message format? Implies a reply type by design. Make it into a verbose reply
        if args[0] in ('OK', 'ER'):
            if not self.queue.active:
                log.msg("Protocol error. Reply to unknown command ('%s')" %(data,), system='OPPO')
                return
            args.insert(0,self.queue.active['command'])

        # Extract command
        cmd = args.pop(0)
        if len(cmd) != 3:
            log.msg("Protocol error, invalid length on command ('%s')" %(data,), system='OPPO')
            return

        # From here on, consider this a valid frame and thus an active connection
        self.setstate('active')

        # Reply type (verbose and short), which is given by the second argument being OK|ER
        if len(args)>0 and args[0] in ('OK', 'ER'):
            if cmd != self.queue.active['command']:
                log.msg("Protocol error, unknown command in reply ('%s')" %(data,), system='OPPO')
                return

            # Send reply back to caller
            if args[0] == 'OK':
                self.queue.callback(args[2:])
            else:
                self.queue.errback(CommandFailedException(args[2:]))
            self.send_next()
            return

        # Status update message we're interested in?
        for ev in eventlist:

            # Consider only responses listed in eventlist
            if ev['cmd'] != cmd:
                continue
            if ev['arg']:
                if len(args)==0 or ev['arg'] != args[0]:
                    continue

            # Pass on to factory to handle the event
            self.parent.event(ev['name'],*args)
            return

        # Not interested in the received message
        log.msg("-IGNORED-", system='OPPO')


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
            log.msg("RAW  <<<  (%s)'%s'" %(len(data),data), system='OPPO')
            self.transport.write(data+self.delimiter)

            # Set timeout
            self.queue.set_timeout(self.timeout, self.timedout)


    def timedout(self):
        # The timeout response is to fail the request and proceed with the next command
        log.msg("Command '%s' timed out" %(self.queue.active['command'],), system='OPPO')
        self.setstate('inactive')
        self.queue.errback(TimeoutException())
        self.send_next()



class Oppo(Endpoint):

    # --- Interfaces
    def get_events(self):
        return [
            'oppo/starting',      # Created oppo object
            'oppo/stopping',      # close() have been called
            'oppo/connected',     # Connection with Oppo has been made
            'oppo/disconnected',  # Lost connection with Oppo
            'oppo/error',         # Connection failed
        ] + [ k['name'] for k in eventlist ]

    def get_actions(self):
        return {
            'oppo/state'   : lambda a : self.protocol.state,
            'oppo/raw'     : lambda a : self.protocol.command(*a.args),
            'oppo/ison'    : lambda a : self.protocol.command('QPW'),
            'oppo/play'    : lambda a : self.protocol.command('PLA'),
            'oppo/pause'   : lambda a : self.protocol.command('PAU'),
            'oppo/stop'    : lambda a : self.protocol.command('STP'),
            'oppo/on'      : lambda a : self.protocol.command('PON'),
            'oppo/off'     : lambda a : self.protocol.command('POF'),
            'oppo/verbose' : lambda a : self.protocol.command('SVM','2'),
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
            self.protocol.setstate('error')
            self.event('oppo/error',e.message)

    def close(self):
        self.event('oppo/stopping')
        if self.sp:
            self.sp.loseConnection()

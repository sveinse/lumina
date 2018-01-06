# -*-python-*-
""" Oppo BDP-103 Media Player interface plugin """
from __future__ import absolute_import

from Queue import Queue

from twisted.internet.defer import Deferred
from twisted.protocols.basic import LineReceiver
from twisted.internet.serialport import EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from twisted.internet.task import LoopingCall

from lumina.node import Node
from lumina.exceptions import CommandRunException, TimeoutException
from lumina.serial import ReconnectingSerialPort


#def ison(result):
#    if result[0]=='ON':
#        return True
#    else:
#        return False


class OppoProtocol(LineReceiver):
    delimiter = '\x0d'
    timeout = 10
    keepalive_interval = 60

    def __init__(self, parent):
        self.parent = parent
        self.master = parent.master
        self.log = parent.log
        self.status = parent.status
        self.queue = Queue()
        self.lastcommand = None


    def connectionMade(self):
        self.log.info("Connected to Oppo")
        self.status.set_YELLOW('Connected, waiting for data')
        self.lastcommand = None

        # Setup a regular keepalive heartbeat (this operation will also
        # set the state green when the response is given)
        self.heartbeat = LoopingCall(self.keepalive)
        self.heartbeat.start(self.keepalive_interval, True)


    def connectionLost(self, reason):  # pylint: disable=W0222
        self.log.info("Lost connection with Oppo: {e}", e=reason.getErrorMessage())
        self.status.set_RED("Lost connection")
        if self.timer:
            self.timer.cancel()
            self.timer = None
        self.heartbeat.stop()
        self.parent.sp.connectionLost(reason)


    def lineReceived(self, data):
        self.log.debug("RAW  >>>  ({l})'{d}'", l=len(data), d=data)

        # Oppo has three incoming message formats:
        #    Short reply:    @(OK|ER) [ARG1 [...]]
        #    Verbose reply:  @CMD (OK|ER) [ARG1 [...]]
        #    Status update:  @CMD [ARG1 [...]]

        # Parse line (skip any chars before '@', but not allow any more after it)
        if '@' not in data:
            self.log.info("Frame error, ignoring junk ('{d}')", d=data)
            return
        data = data[data.find('@'):]
        if '@' in data[1:]:
            self.log.info("Frame error, illegal chars ('{d}')", d=data)
            return
        if len(data) > 25:
            self.log.info("Frame error, line too long ('{d}')", d=data)
            return

        # Split line by spaces. args will be at least one element long
        args = data[1:].split(' ')

        # Log command, but omit logging certain verbose events
        #if args[0] not in ('UTC', ):
        #self.log.info("RAW  >>>  ({l})'{d}'", l=len(data), d=data)

        # Short message format? Implies a reply type by design. Make it into a verbose reply
        if args[0] in ('OK', 'ER'):
            if not self.lastcommand:
                self.log.info("Protocol error. Reply to unknown command ('{d}')", d=data)
                return
            args.insert(0, self.lastcommand)

        # Extract command
        cmd = args.pop(0)
        if len(cmd) != 3:
            self.log.info("Protocol error, invalid length on command ('{d}')", d=data)
            return

        # From here on, consider this a valid frame and thus an active connection
        self.status.set_GREEN()

        # Reply type (verbose and short), which is given by the second argument being OK|ER
        if len(args) > 0 and args[0] in ('OK', 'ER'):
            result = args.pop(0)

            if cmd != self.lastcommand:
                self.log.info("Protocol error, unknown command in reply ('{d}')", d=data)
                return

            # Clean up
            self.lastcommand = None
            self.timer.cancel()
            self.timer = None

            # Send reply back to caller
            if result == 'OK':
                self.defer.callback(args)
            else:
                self.defer.errback(CommandRunException(args[0]))

            # Proceed to the next command
            self.send_next()
            return

        # Status update message we're interested in?
        #for (ev, d) in self.parent.events.items():

        #    # Don't consider events that does not have a payload
        #    if d is None:
        #        continue

        #    # Consider only response types in the events list
        #    if d['cmd'] != cmd:
        #        continue
        #    if d['arg']:
        #        if len(args) == 0 or d['arg'] != args[0]:
        #            continue

        #    # Pass on to factory to handle the event
        #    self.parent.event(ev,*args)
        #    return

        # Not interested in the received message
        self.log.info("-IGNORED-")


    def command(self, command, *args):

        # Compile next request
        a = ' '.join(args)
        if a:
            a = ' ' + a
        msg = '#%s%s' %(command, a)

        defer = Deferred()
        self.queue.put((defer, msg, command))
        self.send_next()
        return defer


    def send_next(self):
        # Don't send new if communication is pending
        if self.lastcommand:
            return

        while self.queue.qsize():
            (defer, msg, command) = self.queue.get(False)

            # Send the command
            self.log.debug("RAW  <<<  ({l})'{d}'", l=len(msg), d=msg)
            self.transport.write(msg.encode('ascii')+self.delimiter)

            # Expect reply, setup timer and return
            #self.lastmsg = msg
            self.lastcommand = command
            self.defer = defer
            self.timer = self.master.reactor.callLater(self.timeout, self.timedout)
            return


    def timedout(self):
        # The timeout response is to fail the request and proceed with the next command
        self.log.info("Command '{c}' timed out", c=self.lastcommand)
        self.status.set_RED('Timeout')
        self.timer = None
        self.lastcommand = None
        self.defer.errback(TimeoutException())
        self.send_next()


    def keepalive(self):
        defer = self.command('QPW')
        defer.addBoth(lambda a: None)



class OppoSerialPort(ReconnectingSerialPort):
    noisy = False
    maxDelay = 10
    factor = 1.6180339887498948

    #def connectionLost(self, reason):
    #    ReconnectingSerialPort.connectionLost(self, reason)

    def connectionFailed(self, reason):
        self.protocol.status.set_RED(reason.getErrorMessage())
        self.protocol.log.error('Oppo connect failed: {e}', e=reason.getErrorMessage())
        ReconnectingSerialPort.connectionFailed(self, reason)



class Oppo(Node):
    ''' Oppo media player interface
    '''

    CONFIG = {
        'port' : dict(default='/dev/ttyUSB0', help='Oppo serial port'),
    }


    # --- Initialization
    def __init__(self):
        self.sp = None


    # --- Interfaces
    def configure(self):

        self.events = (
            #'oppo/starting'     : None,  # Created oppo object
            #'oppo/stopping'     : None,  # close() have been called
            #'oppo/connected'    : None,  # Connection with Oppo has been made
            #'oppo/disconnected' : None,  # Lost connection with Oppo
            #'oppo/error'        : None,  # Connection failed

            #'oppo/off'     : dict(cmd='UPW', arg='0'),
            #'oppo/on'      : dict(cmd='UPW', arg='1'),
            #'oppo/play'    : dict(cmd='UPL', arg='PLAY'),
            #'oppo/pause'   : dict(cmd='UPL', arg='PAUS'),
            #'oppo/stop'    : dict(cmd='UPL', arg='STOP'),
            #'oppo/home'    : dict(cmd='UPL', arg='HOME'),
            #'oppo/nodisc'  : dict(cmd='UPL', arg='DISC'),
            #'oppo/loading' : dict(cmd='UPL', arg='LOAD'),
            #'oppo/closing' : dict(cmd='UPL', arg='CLOS'),
            #'oppo/audio'   : dict(cmd='UAT', arg=None),
        )

        self.commands = {
            'on'      : lambda a: self.c('PON'),
            'off'     : lambda a: self.c('POF'),

            'play'    : lambda a: self.c('PLA'),
            'pause'   : lambda a: self.c('PAU'),
            'stop'    : lambda a: self.c('STP'),
            'eject'   : lambda a: self.c('EJT'),

            'home'    : lambda a: self.c('HOM'),
            'netflix' : lambda a: self.c('APP', 'NFX'),
            'youtube' : lambda a: self.c('APP', 'YOU'),

            #'oppo/raw'     : lambda a : self.c(*a.args),
            #'oppo/ison'    : lambda a : self.c('QPW').addCallback(ison),
            #'oppo/verbose' : lambda a : self.c('SVM','2'),
            #'oppo/status'  : lambda a : self.c('QPL'),
            #'oppo/time'    : lambda a : self.c('QEL'),
            #'oppo/audio'   : lambda a : self.c('QAT'),
        }


    # --- Initialization
    def setup(self):

        self.port = self.master.config.get('port', name=self.name)
        self.protocol = OppoProtocol(self)
        self.sp = OppoSerialPort(self.master.reactor, self.protocol, self.port,
                                 baudrate=9600,
                                 bytesize=EIGHTBITS,
                                 parity=PARITY_NONE,
                                 stopbits=STOPBITS_ONE,
                                 xonxoff=0,
                                 rtscts=0)
        self.sp.log = self.log
        self.sp.connect()


    def close(self):
        Node.close(self)
        self.sp.loseConnection()


    # --- Convenience
    def c(self, *args, **kw):
        return self.protocol.command(*args, **kw)



PLUGIN = Oppo

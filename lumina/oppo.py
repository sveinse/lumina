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


# Translation from Oppo commands to event commands
eventlist = (
    dict(name='oppo/play',  cmd='UPL', arg='PLAY'),
    dict(name='oppo/pause', cmd='UPL', arg='PAUS'),
    dict(name='oppo/stop',  cmd='UPL', arg='STOP'),
    dict(name='oppo/home',  cmd='UPL', arg='HOME'),
    dict(name='oppo/off',   cmd='UPW', arg='0'),
    dict(name='oppo/on',    cmd='UPW', arg='1'),
)


class OppoProtocol(LineReceiver):
    delimiter = '\x0d'
    timeout = 10

    def __init__(self,parent):
        self.parent = parent
        self.queue = Queue()
        self.connected = False


    def connectionMade(self):
        self.connected = True
        self.parent.event('oppo/connected')
        self.send_next()


    def connectionLost(self,reason):
        self.connected = False
        self.parent.event('oppo/disconnected',reason)


    def lineReceived(self, data):
        log.msg("RAW  >>>  (%s)'%s'" %(len(data),data), system='OPPO')

        # Parse line (skip any chars before '@')
        if '@' in data:
            data = data[data.find('@'):]
        #if data[0]!='@':
        #    log.msg("Invalid key, skipping ('%s')" %(data), system='OPPO')
        #    return
        args = data[1:].split(' ')
        cmd = args.pop(0)

        # Log command, but omit logging certain verbose events
        if cmd not in ('UTC', ):
            log.msg("     >>>  %s %s" %(cmd,args), system='OPPO')

        # Reply to active pending command?
        if self.queue.active and self.queue.active['command'] == cmd:
            self.queue.response(*args)
            self.send_next()
            return

        # Status update message we're interested in?
        for ev in eventlist:
            # Consider only responses listed in eventlist
            if ev['cmd'] != cmd:
                continue
            # ..and with listed argument
            if ev['arg'] != args[0]:
                continue

            # Pass on to factory to handle the event
            self.parent.event(ev['name'],*args)
            return

        # Not interested in the message
        log.msg("-IGNORED-", system='OPPO')


    def command(self, command, *args):
        a = ' '.join(args)
        if a:
            a = ' ' + a
        data='#%s%s\x0d' %(command,a)

        d = self.queue.add(data=data, command=command)
        self.send_next()
        return d


    def send_next(self):
        if not self.connected:
            return
        if self.queue.get_next():

            # Send data
            data = self.queue.active['data']
            log.msg("RAW  <<<  (%s)'%s'" %(len(data),data), system='OPPO')
            self.transport.write(data)

            # Set timeout
            self.queue.set_timeout(self.timeout, self.timedout)


    def timedout(self):
        # The timeout response is to fail the request and proceed with the next command
        self.queue.fail()
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
            'oppo/play'    : lambda a : self.protocol.command('PLA'),
            'oppo/pause'   : lambda a : self.protocol.command('PAU'),
            'oppo/stop'    : lambda a : self.protocol.command('STP'),
            'oppo/on'      : lambda a : self.protocol.command('PON'),
            'oppo/off'     : lambda a : self.protocol.command('POF'),
            'oppo/verbose' : lambda a : self.protocol.command('SVM','3'),
        }


    # --- Initialization
    def __init__(self, port):
        self.port = port
        self.sp = None

    def setup(self):
        try:
            self.protocol = OppoProtocol(self)
            self.sp = SerialPort(self.protocol, self.port, reactor,
                                 baudrate=9600,
                                 bytesize=EIGHTBITS,
                                 parity=PARITY_NONE,
                                 stopbits=STOPBITS_ONE,
                                 xonxoff=0,
                                 rtscts=0)
            log.msg('STARTING', system='OPPO')
            self.event('oppo/starting')
        except SerialException as e:
            self.event('oppo/error',e.message)

    def close(self):
        if self.sp:
            self.sp.loseConnection()
        self.event('oppo/stopping')

# -*-python-*-
import os,sys
from twisted.internet import reactor
from twisted.python import log
from twisted.internet.protocol import Protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet.serialport import SerialPort, EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from serial.serialutil import SerialException
from twisted.internet.defer import Deferred

from callback import Callback
from core import Event


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

    def __init__(self,parent):
        self.parent = parent
        self.queue = []
        self.active = None


    def connectionMade(self):
        self.parent.event('oppo/connected')


    def connectionLost(self,reason):
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

        # Reply to active command?
        if self.active and self.active['command'] == cmd:
            (request, self.active) = (self.active, None)
            request['deferred'].callback(args)
            self.send_next()
            return

        # Status update message
        for ev in eventlist:
            # Accept only responses from eventlist
            if ev['cmd'] != cmd:
                continue
            # Ignore unknown args as well
            if ev['arg'] != args[0]:
                continue

            # Pass on to factory to call the callback
            self.parent.event(ev['name'])
            return

        log.msg("-IGNORED-", system='OPPO')


    def command(self, command, *args):
        a = ' '.join(args)
        if a:
            a = ' ' + a
        data='#%s%s\x0d' %(command,a)
        request = {
            'data': data,
            'command': command,
            'deferred': Deferred(),
        }
        self.queue.append(request)
        self.send_next()
        return request['deferred']


    def send_next(self):
        if not self.active and len(self.queue):
            request = self.queue.pop(0)
            self.active = request
            data = request['data']

            log.msg("RAW  <<<  (%s)'%s'" %(len(data),data), system='OPPO')
            self.transport.write(data)

            # FIXME: Add 10s timeout. (Controller has 5 second timeout, which
            # is faster than the protocol's 10s.)



class Oppo(object):

    # -- Initialization
    def __init__(self, port):
        self.port = port
        self.cbevent = Callback()
        self.protocol = OppoProtocol(self)
        self.sp = None

    def setup(self):
        try:
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
            self.event('oppo/error',e)

    def close(self):
        if self.sp:
            self.sp.loseConnection()
        self.event('oppo/stopping')


    # -- Event handler
    def event(self,event,*args):
        self.cbevent.callback(Event(event,*args))
    def add_eventcallback(self, callback, *args, **kw):
        self.cbevent.addCallback(callback, *args, **kw)


    # -- Get list of events and actions
    def get_events(self):
        return [ 'oppo/starting',      # Created oppo object
                 'oppo/stopping',      # close() have been called
                 'oppo/connected',     # Connection with Oppo has been made
                 'oppo/disconnected',  # Lost connection with Oppo
                 'oppo/error' ] + [ k['name'] for k in eventlist ]

    def get_actions(self):
        return {
            'oppo/play'    : lambda a : self.protocol.command('PLA'),
            'oppo/pause'   : lambda a : self.protocol.command('PAU'),
            'oppo/stop'    : lambda a : self.protocol.command('STP'),
            'oppo/on'      : lambda a : self.protocol.command('PON'),
            'oppo/off'     : lambda a : self.protocol.command('POF'),
            'oppo/verbose' : lambda a : self.protocol.command('SVM','3'),
         }

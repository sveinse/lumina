# -*-python-*-
import os,sys

from twisted.internet import reactor
from twisted.python import log
from twisted.internet.protocol import Protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet.serialport import SerialPort, EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from serial.serialutil import SerialException

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


    def lineReceived(self, data):
        #log.msg("     >>>  (%s)'%s'" %(len(data),data), system='Oppo')

        if data[0]!='@':
            log.msg("Invalid key, skipping ('%s')" %(data), system='Oppo')
            return
        args = data[1:].split(' ')
        cmd = args.pop(0)

        # Do not log certain events
        if cmd not in ('UTC', ):
            log.msg("     >>>  %s %s" %(cmd,args), system='Oppo')

        for ev in eventlist:
            if ev['cmd'] != cmd:
                continue
            if ev['arg'] != args[0]:
                continue

            # Pass on to factory to call the callback
            self.parent._event(ev['name'])
            break


    def command(self, command, *args):
        a = ' '.join(args)
        if a:
            a = ' ' + a
        data='#%s%s\x0d' %(command,a)
        log.msg("     <<<  (%s)'%s'" %(len(data),data), system='Oppo')
        log.msg("%s" %(dir(self)))
        self.transport.write(data)



class Oppo:

    def __init__(self, port):
        self.port = port
        self.cbevent = Callback()
        self.protocol = OppoProtocol(self)

    def setup(self):
        try:
            SerialPort(self.protocol, self.port, reactor,
                       baudrate=9600,
                       bytesize=EIGHTBITS,
                       parity=PARITY_NONE,
                       stopbits=STOPBITS_ONE,
                       xonxoff=0,
                       rtscts=0)
            log.msg('STARTING', system='Oppo')
            self._event('oppo/starting')
        except SerialException as e:
            self._event('oppo/error',e)

    # Internal event received, fire external handler
    def _event(self,event,*args):
        self.cbevent.callback(Event(event,*args))

    # Register event handler
    def add_eventcallback(self, callback, *args, **kw):
        self.cbevent.addCallback(callback, *args, **kw)

    # Get supported list of events (incoming)
    def get_events(self):
        return [ k['name'] for k in eventlist ]

    # Get supported list of actions (outgoing)
    def get_actions(self):
        return {
            'oppo/play' : lambda a : self.protocol.command('PLA'),
            'oppo/pause': lambda a : self.protocol.command('PAU'),
            'oppo/stop' : lambda a : self.protocol.command('STP'),
            'oppo/on'   : lambda a : self.protocol.command('PON'),
            'oppo/off'  : lambda a : self.protocol.command('POF'),
         }

# -*-python-*-
import os,sys

from twisted.internet import reactor
from twisted.python import log
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.internet.defer import Deferred

from endpoint import Endpoint
from queue import Queue
from exceptions import *



# Can be tested with
#    socat UNIX-LISTEN:/tmp/TelldusEvents -
#    socat UNIX-LISTEN:/tmp/TelldusClient -
#
# On target communicting with Telldus:
#     socat UNIX-connect:/tmp/TelldusEvents -
#     socat UNIX-connect:/tmp/TelldusClient -



def getnextelement(data):
    ''' Return the (next,remain) raw data element from data.

        The syntax is:  NN:string  where NN is a number indicating length of string
                        iNs        where N is am integer number
    '''
    if data and data[0] in '0123456789':
        n = data.split(':',1)
        l = int(n[0])
        return (n[1][:l], n[1][l:])
    elif data and data[0]=='i':
        n = data.split('s',1)
        l = int(n[0][1:])
        return (l,n[1])
    else:
        return (None,data)



def parsestream(data):
    ''' Parse self.data byte stream into list of elements in self.elements '''
    el = [ ]

    # Split the raw data into list of objects (string or integer)
    while True:
        (element,data) = getnextelement(data)
        if element is None:
            return el,data
        el.append(element)



def parseelements(elements):
    ''' Parse elements into events '''
    events = [ ]

    # Extract events from list of objects
    while elements:
        cmd = elements.pop(0)
        #log.msg("%s  %s" %(cmd,elements))

        # Expected commands and their parameter length
        cmdsize = {
            'TDSensorEvent': 6,
            'TDRawDeviceEvent': 2,
            'TDControllerEvent': 4,
            'TDDeviceEvent': 3,
        }

        if cmd not in cmdsize:
            log.msg("Unknown command '%s', dropping %s" %(cmd, elements), system='TD')
            elements = [ ]
            break

        l = cmdsize[cmd]

        if l > len(elements):
            # Does not got enough data for command. Stop and postpone processing
            log.msg("Missing elements for command '%s', got %s, needs %s args." %(cmd,elements,l), system='TD')
            elements = [ ]
            break

        l = cmdsize[cmd]
        args = elements[:l]
        elements = elements[l:]
        events.append( [cmd] + args )

    return (events, elements)



def parserawargs(args):
    ''' Split the 'key1:data1;key2:data2;...' string syntax into a dictionary '''

    alist = args.split(';')
    adict = dict()
    for a in alist:
        if a:
            o = a.split(':')
            adict[o[0]]=o[1]
    return adict



def generate(args):
    s=''
    for a in args:
        if type(a) is str:
            s+='%s:%s' %(len(a),a)
        elif type(a) is int:
            s+='i%ds' %(a)
    return s



class TelldusFactory(ClientFactory):
    noisy = False

    def __init__(self, protocol, parent):
        self.protocol = protocol
        self.parent = parent

    def buildProtocol(self, addr):
        return self.protocol

    def clientConnectionFailed(self, connector, reason):
        self.protocol.setstate('error',self.protocol.path,reason.getErrorMessage())



class TelldusIn(Protocol):
    ''' Class for incoming Telldus events '''

    noisy = False
    name = 'Event'
    path = '/tmp/TelldusEvents'
    system = 'TD/IN'


    def __init__(self,parent):
        self.state = 'init'
        self.parent = parent
        self.factory = TelldusFactory(self, self.parent)


    def setstate(self,state,*args):
        (old, self.state) = (self.state, state)
        if state != old:
            log.msg("STATE change: '%s' --> '%s'" %(old,state), system=self.system)
        self.parent.changestate(self,self.state,*args)


    def connect(self):
        self.setstate('connecting')
        reactor.connectUNIX(self.path, self.factory)


    def connectionMade(self):
        self.setstate('connected')
        self.data = ''
        self.elements = [ ]


    def connectionLost(self, reason):
        self.setstate('closed', reason.getErrorMessage())


    def disconnect(self):
        if self.state in ('connected','active'):
            self.transport.loseConnection()


    def dataReceived(self, data):
        #log.msg("     >>>  (%s)'%s'" %(len(data),data), system=self.system)

        data = self.data + data

        # Interpret the data
        (elements, data) = parsestream(data)
        (events, elements) = parseelements(elements)

        # Save remaining data for next call (incomplete frame received)
        self.data = data
        self.elements = elements

        # At this point, we can consider the connection active
        self.setstate('active')

        # Iterate over the received events
        for event in events:
            self.parent.parse_event(event)



class TelldusOut(Protocol):
    ''' Class for outgoing Telldus commands '''

    noisy = False
    name = 'Client'
    path = '/tmp/TelldusClient'
    timeout = 5
    system = 'TD/OUT'


    # This object is connected when data is about to be sent and closed right after.
    # The normal flow is:
    #   command -> send_next() -> connectionMade() -> dataReceived()
    #   -> disconnect() -> connectionLost() [ -> send_next() ... ]

    def __init__(self,parent):
        self.state = 'init'
        self.parent = parent
        self.queue = Queue()
        self.factory = TelldusFactory(self, self.parent)


    def setstate(self,state,*args):
        (old, self.state) = (self.state, state)
        if state != old:
            log.msg("STATE change: '%s' --> '%s'" %(old,state), system=self.system)
        self.parent.changestate(self,self.state,*args)


    def connectionMade(self):
        self.setstate('connected')
        data = self.queue.active['data']
        log.msg("     <<<  (%s)'%s'" %(len(data),data), system=self.system)
        self.transport.write(data)


    def connectionLost(self, reason):
        self.setstate('closed', reason.getErrorMessage())
        self.send_next()


    def disconnect(self):
        if self.state in ('connected','active'):
            self.transport.loseConnection()


    def dataReceived(self, data):
        self.setstate('active')
        log.msg("     >>>  (%s)'%s'" %(len(data),data), system=self.system)
        (elements, data) = parsestream(data)
        #log.msg("          %s" %(elements), system=self.system)
        self.disconnect()
        self.queue.callback(elements)


    def command(self, cmd):
        data = generate(cmd)
        d = self.queue.add(data=data, command=cmd)
        self.send_next()
        return d


    def send_next(self):
        #if self.state not in (''):
        #    return

        if self.queue.get_next() is not None:
            reactor.connectUNIX(self.path, self.factory)
            self.queue.set_timeout(self.timeout, self.timedout)


    def timedout(self):
        # The timeout response is to fail the request and proceed with the next command
        log.msg("Command '%s' timed out" %(self.queue.active['command'],), system=self.system)
        self.setstate('inactive')
        self.queue.errback(TimeoutException())
        self.send_next()



class Telldus(Endpoint):
    system = 'TD'
    name = 'TELLDUS'

    # --- Interfaces
    def configure(self):
        self.events = {
            'td/starting'    : None,
            'td/connected'   : None,
            'td/error'       : None,

            # Remote control
            'remote/g/on'    : dict(house=14244686, group=1, unit=1, method='turnon'),
            'remote/g/off'   : dict(house=14244686, group=1, unit=1, method='turnoff'),
            'remote/1/on'    : dict(house=14244686, group=0, unit=1, method='turnon'),
            'remote/1/off'   : dict(house=14244686, group=0, unit=1, method='turnoff'),
            'remote/2/on'    : dict(house=14244686, group=0, unit=2, method='turnon'),
            'remote/2/off'   : dict(house=14244686, group=0, unit=2, method='turnoff'),
            'remote/3/on'    : dict(house=14244686, group=0, unit=3, method='turnon'),
            'remote/3/off'   : dict(house=14244686, group=0, unit=3, method='turnoff'),
            'remote/4/on'    : dict(house=14244686, group=0, unit=4, method='turnon'),
            'remote/4/off'   : dict(house=14244686, group=0, unit=4, method='turnoff'),
            'remote/5/on'    : dict(house=14244686, group=0, unit=5, method='turnon'),
            'remote/5/off'   : dict(house=14244686, group=0, unit=5, method='turnoff'),
            'remote/6/on'    : dict(house=14244686, group=0, unit=6, method='turnon'),
            'remote/6/off'   : dict(house=14244686, group=0, unit=6, method='turnoff'),
            'remote/7/on'    : dict(house=14244686, group=0, unit=7, method='turnon'),
            'remote/7/off'   : dict(house=14244686, group=0, unit=7, method='turnoff'),
            'remote/8/on'    : dict(house=14244686, group=0, unit=8, method='turnon'),
            'remote/8/off'   : dict(house=14244686, group=0, unit=8, method='turnoff'),
            'remote/9/on'    : dict(house=14244686, group=0, unit=9, method='turnon'),
            'remote/9/off'   : dict(house=14244686, group=0, unit=9, method='turnoff'),
            'remote/10/on'   : dict(house=14244686, group=0, unit=10, method='turnon'),
            'remote/10/off'  : dict(house=14244686, group=0, unit=10, method='turnoff'),
            'remote/11/on'   : dict(house=14244686, group=0, unit=11, method='turnon'),
            'remote/11/off'  : dict(house=14244686, group=0, unit=11, method='turnoff'),
            'remote/12/on'   : dict(house=14244686, group=0, unit=12, method='turnon'),
            'remote/12/off'  : dict(house=14244686, group=0, unit=12, method='turnoff'),
            'remote/13/on'   : dict(house=14244686, group=0, unit=13, method='turnon'),
            'remote/13/off'  : dict(house=14244686, group=0, unit=13, method='turnoff'),
            'remote/14/on'   : dict(house=14244686, group=0, unit=14, method='turnon'),
            'remote/14/off'  : dict(house=14244686, group=0, unit=14, method='turnoff'),
            'remote/15/on'   : dict(house=14244686, group=0, unit=15, method='turnon'),
            'remote/15/off'  : dict(house=14244686, group=0, unit=15, method='turnoff'),
            'remote/16/on'   : dict(house=14244686, group=0, unit=16, method='turnon'),
            'remote/16/off'  : dict(house=14244686, group=0, unit=16, method='turnoff'),

            # Loftstue upper
            'wallsw1/on'     : dict(house=366702,   group=0, unit=1, method='turnon'),
            'wallsw1/off'    : dict(house=366702,   group=0, unit=1, method='turnoff'),

            # Loftstue lower
            'wallsw2/on'     : dict(house=392498,   group=0, unit=1, method='turnon'),
            'wallsw2/off'    : dict(house=392498,   group=0, unit=1, method='turnoff'),

            # Mandolyn devices
            'temp/ute'       : dict(temp=11),
            'temp/kjeller'   : dict(temp=12),

            # Nexa/proove devices
            'temp/fryseskap' : dict(temp=247),
            'temp/loftute'   : dict(temp=135),
            'temp/kino'      : dict(temp=151),
        }

        self.commands = {
            'td/state'      : lambda a : (self.inport.state, self.outport.state),
            'td/ison'       : lambda a : self.ison(),

            'td/on'         : lambda a : self.turnOn(a.args[0]),
            'td/off'        : lambda a : self.turnOff(a.args[0]),
            'td/dim'        : lambda a : self.dim(a.args[0],a.args[1]),

            'lys/on'        : lambda a : self.turnOn(100),
            'lys/off'       : lambda a : self.turnOff(100),
            'lys/dim'       : lambda a : self.dim(100, a.args[0]),
            'lys/tak/on'    : lambda a : self.turnOn(101),
            'lys/tak/off'   : lambda a : self.turnOff(101),
            'lys/tak/dim'   : lambda a : self.dim(101, a.args[0]),
            'lys/bord/on'   : lambda a : self.turnOn(105),
            'lys/bord/off'  : lambda a : self.turnOff(105),
            'lys/bord/dim'  : lambda a : self.dim(105, a.args[0]),
            'led/pwr/on'    : lambda a : self.turnOn(106),
            'led/pwr/off'   : lambda a : self.turnOff(106),
        }


    # --- Initialization
    def __init__(self):
        self.inport = TelldusIn(self)
        self.outport = TelldusOut(self)

    def setup(self):
        self.event('td/starting')
        self.inport.connect()

    def close(self):
        self.event('td/stopping')
        self.inport.disconnect()
        self.outport.disconnect()


    # --- Callbacks
    def changestate(self,cls,state,*args):
        if cls == self.inport:
            if state == 'connected':
                self.event('td/connected')
            elif state == 'closed':
                self.event('td/disconnected',*args)
            elif state == 'error':
                self.event('td/error',*args)
        elif cls == self.outport:
            if state == 'error':
                self.event('td/error',*args)


    # --- Commands
    def ison(self):
        if self.inport.state in ('connected','active'):
            return True
        else:
            return False

    def turnOn(self,num):
        cmd = ( 'tdTurnOn', num )
        return self.outport.command(cmd)

    def turnOff(self,num):
        cmd = ( 'tdTurnOff', num )
        return self.outport.command(cmd)

    def dim(self,num, val):
        cmd = ( 'tdDim', num, val )
        return self.outport.command(cmd)


    # --- Event filter (located here to keep TelldusInport() clean
    def parse_event(self, event):
        cmd = event[0]

        #log.msg("     >>>  %s  %s" %(cmd,event[1:]), system=self.inport.system)

        if cmd == 'TDSensorEvent':
            # ignoring sensor events as we handle them as raw device events
            return

        elif cmd == 'TDRawDeviceEvent':

            args = parserawargs(event[1])
            #log.msg("     >>>  %s  %s" %(cmd,args), system=self.inport.system)

            if 'protocol' not in args:
                log.msg("Missing protocol from %s, dropping event" %(cmd),
                        system=self.inport.system)
                return

            #if args['protocol'] != 'arctech':
            #    #log.msg("Ignoring unknown protocol '%s' in '%s', dropping event" %(args['protocol'],cmd), system=self.inport.system)
            #    continue

            # Check for matches in eventlist
            if args['protocol'] == 'arctech':

                for (ev,d) in self.events.items():

                    # Disregard objects without dict and without 'house' in dict
                    if d is None or 'house' not in d:
                        continue

                    # Find the matching entry
                    if str(d['house']) != args['house']:
                        continue
                    if str(d['group']) != args['group']:
                        continue
                    if str(d['unit']) != args['unit']:
                        continue
                    if d['method'] != args['method']:
                        continue

                    # Match found, process it as an event
                    self.event(ev)
                    return

            elif args['protocol'] == 'mandolyn' or args['protocol'] == 'fineoffset':

                for (ev,d) in self.events.items():

                    # Disregard objects without dict and without 'temp' in dict
                    if d is None or 'temp' not in d:
                        continue

                    # Find the matching entry
                    if str(d['temp']) != args['id']:
                        continue

                    # Match found, process it as an event
                    if 'humidity' in args:
                        self.event("%s{%s,%s}" %(ev,args['temp'],args['humidity']))
                    else:
                        self.event("%s{%s}" %(ev,args['temp']))
                    return

                # Not interested in logging temp events we don't subscribe to
                return

        # Ignore the other events
        log.msg("Ignoring '%s' %s" %(cmd,event[1:]), system=self.inport.system)

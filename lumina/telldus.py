# -*-python-*-
import os,sys

from twisted.internet import reactor
from twisted.python import log
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.internet.defer import Deferred
from callback import Callback
from event import Action, Event

# Can be tested with
#    socat UNIX-LISTEN:/tmp/TelldusEvents -
#    socat UNIX-LISTEN:/tmp/TelldusClient -
#
# On target communicting with Telldus:
#     socat UNIX-connect:/tmp/TelldusEvents -
#     socat UNIX-connect:/tmp/TelldusClient -


eventlist = (
    dict(name='td/remote/g/on',  house=14244686, group=1, unit=1, method='turnon'),
    dict(name='td/remote/g/off', house=14244686, group=1, unit=1, method='turnoff'),
    dict(name='td/remote/1/on',  house=14244686, group=0, unit=1, method='turnon'),
    dict(name='td/remote/1/off', house=14244686, group=0, unit=1, method='turnoff'),
    dict(name='td/remote/2/on',  house=14244686, group=0, unit=2, method='turnon'),
    dict(name='td/remote/2/off', house=14244686, group=0, unit=2, method='turnoff'),
    dict(name='td/remote/3/on',  house=14244686, group=0, unit=3, method='turnon'),
    dict(name='td/remote/3/off', house=14244686, group=0, unit=3, method='turnoff'),
    dict(name='td/remote/4/on',  house=14244686, group=0, unit=4, method='turnon'),
    dict(name='td/remote/4/off', house=14244686, group=0, unit=4, method='turnoff'),

    dict(name='td/wallsw1/on',   house=366702,   group=0, unit=1, method='turnon'),
    dict(name='td/wallsw1/off',  house=366702,   group=0, unit=1, method='turnoff'),

    dict(name='td/wallsw2/on',   house=392498,   group=0, unit=1, method='turnon'),
    dict(name='td/wallsw2/off',  house=392498,   group=0, unit=1, method='turnoff'),
)


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
        #log.msg(n)
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
            log.msg("Unknown command '%s', dropping %s" %(cmd, elements), system='Telldus')
            elements = [ ]
            break

        l = cmdsize[cmd]

        if l > len(elements):
            # Does not got enough data for command. Stop and postpone processing
            log.msg("Missing elements for command '%s', got %s, needs %s args." %(cmd,elements,l), system='Telldus')
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
    def __init__(self, protocol, parent):
        self.protocol = protocol
        self.parent = parent

    def buildProtocol(self, addr):
        return self.protocol

    def clientConnectionFailed(self, connector, reason):
        self.parent.error(self, reason)



class TelldusEvents(Protocol):
    name = 'Event'
    path = '/tmp/TelldusEvents'

    def __init__(self,parent):
        self.parent = parent
        self.connected = False

    def connect(self):
        factory = TelldusFactory(self, self.parent)
        reactor.connectUNIX(self.path, factory)
        self.factory = factory

    def connectionMade(self):
        log.msg("%s connected" %(self.name), system='Telldus')
        self.data = ''
        self.elements = [ ]
        self.connected = True
        self.parent.connected(self)

    def connectionLost(self, reason):
        log.msg("%s connection lost: %s" %(self.name,reason), system='Telldus')
        if self.connected:
            self.connected = False
            self.parent.error(self,reason)

    def disconnect(self):
        if self.connected:
            self.connected = False
            self.transport.loseConnection()

    def dataReceived(self, data):
        #log.msg("     >>>  (%s)'%s'" %(len(data),data), system='Telldus')

        data = self.data + data

        # Interpret the data
        (elements, data) = parsestream(data)
        (events, elements) = parseelements(elements)

        # Save remaining data (incomplete frame received)
        self.data = data
        self.elements = elements

        # Iverate over the events
        for event in events:
            cmd = event[0]

            log.msg("     >>>  %s  %s" %(cmd,event[1:]), system='Telldus')

            if cmd == 'TDRawDeviceEvent':

                args = parserawargs(event[1])
                if 'protocol' not in args:
                    log.msg("Missing protocol from %s, dropping event" %(cmd), system='Telldus')
                    continue

                if args['protocol'] != 'arctech':
                    #log.msg("Ignoring unknown protocol '%s' in '%s', dropping event" %(args['protocol'],cmd))
                    continue

                # Check for matches in eventlist
                for ev in eventlist:
                    if str(ev['house']) != args['house']:
                        continue
                    if str(ev['group']) != args['group']:
                        continue
                    if str(ev['unit']) != args['unit']:
                        continue
                    if ev['method'] != args['method']:
                        continue

                    # Pass on to factory to call the callback
                    self.parent.event(ev['name'])
                    break

            # Ignore the other events
            #log.msg("Ignoring unhandled command '%s', dropping" %(cmd))



class TelldusClient(Protocol):
    name = 'Client'
    path = '/tmp/TelldusClient'
    queue = [ ]
    active = None

    def __init__(self,parent):
        self.parent = parent
        self.data = ''
        self.elements = [ ]
        self.connected = False

        self.factory = TelldusFactory(self, self.parent)

    def connect(self):
        #factory = TelldusFactory(self, self.parent)
        reactor.connectUNIX(self.path, self.factory)
        #self.factory = factory

    def connectionMade(self):
        log.msg("%s connected" %(self.name), system='Telldus')
        self.data = ''
        self.elements = [ ]
        self.connected = True
        (data,d) = self.active
        log.msg("     <<<  (%s)'%s'" %(len(data),data), system='Telldus')
        self.transport.write(data)

    def connectionLost(self, reason):
        log.msg("%s connection closed" %(self.name), system='Telldus')
        self.connected = False
        self.active = None
        self.sendNextCommand()

    def disconnect(self):
        if self.connected:
            self.transport.loseConnection()

    def dataReceived(self, data):
        #log.msg("     >>>  (%s)'%s'" %(len(data),data), system='Telldus')
        data = self.data + data
        (elements, data) = parsestream(data)
        #log.msg("          %s" %(elements), system='Telldus')
        (m,d) = self.active
        self.disconnect()
        d.callback(elements)

    def sendCommand(self, cmd):
        data = generate(cmd)
        d = Deferred()
        self.queue.append( (data, d) )
        self.sendNextCommand()
        return d

    def sendNextCommand(self):
        if not self.queue:
            return
        if self.active:
            return
        self.active = self.queue.pop(0)
        self.connect()



class Telldus:

    def __init__(self):
        self.cbevent = Callback()

        self.events = TelldusEvents(self)
        self.client = TelldusClient(self)

        reactor.addSystemEventTrigger('before','shutdown',self.close)


    # Initiate connection (can be run prior to starting the reactor)
    def setup(self):
        log.msg('STARTING', system='Telldus')
        self.event('td/starting')
        self.events.connect()


    # Register event callbacks
    def add_eventcallback(self, callback, *args, **kw):
        self.cbevent.addCallback(callback, *args, **kw)
    def event(self,event,*args):
        self.cbevent.callback(Event(event,*args))


    # Yeah, you know what this is
    def close(self):
        log.msg("Close called", system='Telldus')
        if self.events:
            self.events.disconnect()
        if self.client:
            self.client.disconnect()


    # Return list of actions this class supports
    def get_actiondict(self):
        return {
            'td/lights/on'  : lambda a : self.turnOn(4),
            'td/lights/off' : lambda a : self.turnOff(4),
            'td/lights/dim' : lambda a : self.dim(4, a.args[0]),
            'td/roof/off'   : lambda a : self.turnOff(5),
            'td/table/dim'  : lambda a : self.dim(1, a.args[0]),
        }


    # Protocol and factory callback points
    def error(self, who, reason):
        ''' Called if connections fails '''
        log.err("Error: %s, %s" %(who,reason), system='Telldus')
        self.event('td/error', who, reason)

    def connected(self, who):
        ''' Called when connection is established '''
        self.event('td/connected')



    # Telldus Actions
    def turnOn(self,num):
        cmd = ( 'tdTurnOn', num )
        return self.client.sendCommand(cmd)

    def turnOff(self,num):
        cmd = ( 'tdTurnOff', num )
        return self.client.sendCommand(cmd)

    def dim(self,num, val):
        cmd = ( 'tdDim', num, val )
        return self.client.sendCommand(cmd)



if __name__ == "__main__":
    from twisted.python.log import startLogging
    startLogging(sys.stdout)

    def error(reason,td):
        log.msg("ERROR",reason)
        reactor.stop()

    def ready(result,td):
        log.msg("READY",result)
        d = td.turnOn(1)
        d = td.turnOn(2)
        d = td.turnOn(3)

    def event(result,td):
        log.msg("EVENT",result)

    td = Telldus()
    d = td.setup()
    td.addCallbackReady(ready,td)
    td.addCallbackError(error,td)
    td.addCallbackEvent(event,td)
    d = td.turnOn(1)
    d = td.turnOn(2)
    d = td.turnOn(3)

    reactor.run()

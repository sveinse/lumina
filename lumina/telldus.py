# -*-python-*-
import os,sys

from twisted.internet import reactor
from twisted.python import log
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.internet.defer import Deferred

from endpoint import Endpoint
from queue import Queue


class TelldusException(Exception):
    pass
class FrameException(TelldusException):
    pass
class NotConnectedException(TelldusException):
    pass
class TimeoutException(TelldusException):
    pass


# Can be tested with
#    socat UNIX-LISTEN:/tmp/TelldusEvents -
#    socat UNIX-LISTEN:/tmp/TelldusClient -
#
# On target communicting with Telldus:
#     socat UNIX-connect:/tmp/TelldusEvents -
#     socat UNIX-connect:/tmp/TelldusClient -

# NOTE: The list of td actions is listed under get_action(), around line 392

eventlist = (
    # Remote control
    dict(name='remote/g/on',  house=14244686, group=1, unit=1, method='turnon'),
    dict(name='remote/g/off', house=14244686, group=1, unit=1, method='turnoff'),
    dict(name='remote/1/on',  house=14244686, group=0, unit=1, method='turnon'),
    dict(name='remote/1/off', house=14244686, group=0, unit=1, method='turnoff'),
    dict(name='remote/2/on',  house=14244686, group=0, unit=2, method='turnon'),
    dict(name='remote/2/off', house=14244686, group=0, unit=2, method='turnoff'),
    dict(name='remote/3/on',  house=14244686, group=0, unit=3, method='turnon'),
    dict(name='remote/3/off', house=14244686, group=0, unit=3, method='turnoff'),
    dict(name='remote/4/on',  house=14244686, group=0, unit=4, method='turnon'),
    dict(name='remote/4/off', house=14244686, group=0, unit=4, method='turnoff'),
    dict(name='remote/5/on',  house=14244686, group=0, unit=5, method='turnon'),
    dict(name='remote/5/off', house=14244686, group=0, unit=5, method='turnoff'),
    dict(name='remote/6/on',  house=14244686, group=0, unit=6, method='turnon'),
    dict(name='remote/6/off', house=14244686, group=0, unit=6, method='turnoff'),
    dict(name='remote/7/on',  house=14244686, group=0, unit=7, method='turnon'),
    dict(name='remote/7/off', house=14244686, group=0, unit=7, method='turnoff'),
    dict(name='remote/8/on',  house=14244686, group=0, unit=8, method='turnon'),
    dict(name='remote/8/off', house=14244686, group=0, unit=8, method='turnoff'),
    dict(name='remote/9/on',  house=14244686, group=0, unit=9, method='turnon'),
    dict(name='remote/9/off', house=14244686, group=0, unit=9, method='turnoff'),
    dict(name='remote/10/on',  house=14244686, group=0, unit=10, method='turnon'),
    dict(name='remote/10/off', house=14244686, group=0, unit=10, method='turnoff'),
    dict(name='remote/11/on',  house=14244686, group=0, unit=11, method='turnon'),
    dict(name='remote/11/off', house=14244686, group=0, unit=11, method='turnoff'),
    dict(name='remote/12/on',  house=14244686, group=0, unit=12, method='turnon'),
    dict(name='remote/12/off', house=14244686, group=0, unit=12, method='turnoff'),
    dict(name='remote/13/on',  house=14244686, group=0, unit=13, method='turnon'),
    dict(name='remote/13/off', house=14244686, group=0, unit=13, method='turnoff'),
    dict(name='remote/14/on',  house=14244686, group=0, unit=14, method='turnon'),
    dict(name='remote/14/off', house=14244686, group=0, unit=14, method='turnoff'),
    dict(name='remote/15/on',  house=14244686, group=0, unit=15, method='turnon'),
    dict(name='remote/15/off', house=14244686, group=0, unit=15, method='turnoff'),
    dict(name='remote/16/on',  house=14244686, group=0, unit=16, method='turnon'),
    dict(name='remote/16/off', house=14244686, group=0, unit=16, method='turnoff'),

    # Loftstue upper
    dict(name='wallsw1/on',   house=366702,   group=0, unit=1, method='turnon'),
    dict(name='wallsw1/off',  house=366702,   group=0, unit=1, method='turnoff'),

    # Loftstue lower
    dict(name='wallsw2/on',   house=392498,   group=0, unit=1, method='turnon'),
    dict(name='wallsw2/off',  house=392498,   group=0, unit=1, method='turnoff'),
)

templist = (
    # Mandolyn devices
    #dict(name='temp/ute', id=11),
    #dict(name='temp/kjeller', id=12),

    # Nexa/proove devices
    #dict(name='temp/fryseskap', id=247),
    #dict(name='temp/loftute', id=135),
    #dict(name='temp/kino', id=151),
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


    def __init__(self,parent):
        self.state = 'init'
        self.parent = parent
        self.factory = TelldusFactory(self, self.parent)


    def setstate(self,state,*args):
        (old, self.state) = (self.state, state)
        if state != old:
            log.msg("STATE change: '%s' --> '%s'" %(old,state), system='TD/IN')
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
        #log.msg("     >>>  (%s)'%s'" %(len(data),data), system='TD')

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
            log.msg("STATE change: '%s' --> '%s'" %(old,state), system='TD/OUT')
        self.parent.changestate(self,self.state,*args)


    def connectionMade(self):
        self.setstate('connected')
        data = self.queue.active['data']
        log.msg("     <<<  (%s)'%s'" %(len(data),data), system='TD/OUT')
        self.transport.write(data)


    def connectionLost(self, reason):
        self.setstate('closed', reason.getErrorMessage())
        self.send_next()


    def disconnect(self):
        if self.state in ('connected','active'):
            self.transport.loseConnection()


    def dataReceived(self, data):
        self.setstate('active')
        log.msg("     >>>  (%s)'%s'" %(len(data),data), system='TD/OUT')
        (elements, data) = parsestream(data)
        #log.msg("          %s" %(elements), system='TD')
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
        log.msg("Command '%s' timed out" %(self.queue.active['command'],), system='TD/OUT')
        self.setstate('inactive')
        self.queue.errback(TimeoutException())
        self.send_next()



class Telldus(Endpoint):

    # --- Interfaces
    def get_events(self):
        return [
            'td/starting',
            'td/connected',
            'td/error',
        ] + [ k['name'] for k in eventlist ] + [ k['name'] for k in templist ]

    def get_actions(self):
        return {
            'td/state'     : lambda a : (self.inport.state, self.outport.state),

            'td/on'        : lambda a : self.turnOn(a.args[0]),
            'td/off'       : lambda a : self.turnOff(a.args[0]),
            'td/dim'       : lambda a : self.dim(a.args[0],a.args[1]),

            'lys/on'       : lambda a : self.turnOn(100),
            'lys/off'      : lambda a : self.turnOff(100),
            'lys/dim'      : lambda a : self.dim(100, a.args[0]),
            'lys/tak/on'   : lambda a : self.turnOn(101),
            'lys/tak/off'  : lambda a : self.turnOff(101),
            'lys/tak/dim'  : lambda a : self.dim(101, a.args[0]),
            'lys/bord/on'  : lambda a : self.turnOn(105),
            'lys/bord/off' : lambda a : self.turnOff(105),
            'lys/bord/dim' : lambda a : self.dim(105, a.args[0]),
            'led/pwr/on'   : lambda a : self.turnOn(106),
            'led/pwr/off'  : lambda a : self.turnOff(106),
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
        if self.inport:
            self.inport.disconnect()
        if self.outport:
            self.outport.disconnect()


    # --- Notification on internal state changes
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


    # --- Telldus Actions
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

        #log.msg("     >>>  %s  %s" %(cmd,event[1:]), system='TD')

        if cmd == 'TDSensorEvent':
            # ignoring sensor events as we handle them as raw device events
            return

        elif cmd == 'TDRawDeviceEvent':

            args = parserawargs(event[1])
            #log.msg("     >>>  %s  %s" %(cmd,args), system='TD')

            if 'protocol' not in args:
                log.msg("Missing protocol from %s, dropping event" %(cmd), system='TD')
                return

            #if args['protocol'] != 'arctech':
            #    #log.msg("Ignoring unknown protocol '%s' in '%s', dropping event" %(args['protocol'],cmd))
            #    continue

            # Check for matches in eventlist
            if args['protocol'] == 'arctech':

                for ev in eventlist:
                    if str(ev['house']) != args['house']:
                        continue
                    if str(ev['group']) != args['group']:
                        continue
                    if str(ev['unit']) != args['unit']:
                        continue
                    if ev['method'] != args['method']:
                        continue

                    self.event(ev['name'])
                    return

            elif args['protocol'] == 'mandolyn' or args['protocol'] == 'fineoffset':

                for ev in templist:
                    if str(ev['id']) != args['id']:
                        continue

                    if 'humidity' in args:
                        self.event("%s{%s,%s}" %(ev['name'],args['temp'],args['humidity']))
                    else:
                        self.event("%s{%s}" %(ev['name'],args['temp']))
                    return

                # Not interested in logging temp events we don't subscribe to
                return

        # Ignore the other events
        log.msg("Ignoring '%s' %s" %(cmd,event[1:]), system='TD')




################################################################
#
#  TESTING
#
################################################################
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

# -*-python-*-
#from __future__ import absolute_import

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory, Protocol, ReconnectingClientFactory
from twisted.internet.defer import Deferred

from ..leaf import Leaf
from ..state import State
from ..event import Event
from ..exceptions import *
from ..log import *
from lumina import utils

# Import responder rules from separate file
from .rules import telldus_config


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



def parseelements(elements,system=None):
    ''' Parse elements into events '''
    events = [ ]

    # Extract events from list of objects
    while elements:
        cmd = elements.pop(0)
        #log("%s  %s" %(cmd,elements))

        # Expected commands and their parameter length
        cmdsize = {
            'TDSensorEvent': 6,
            'TDRawDeviceEvent': 2,
            'TDControllerEvent': 4,
            'TDDeviceEvent': 3,
        }

        if cmd not in cmdsize:
            log("Unknown command '%s', dropping %s" %(cmd, elements), system=system)
            elements = [ ]
            break

        l = cmdsize[cmd]

        if l > len(elements):
            # Does not got enough data for command. Stop and postpone processing
            log("Missing elements for command '%s', got %s, needs %s args." %(cmd,elements,l), system=system)
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
    ''' Encode args into telldus string encoding, which is '<LEN>:string' and 'i<NUM>s' for
        integer. '''
    s=''
    for a in args:
        if type(a) is str:
            s+='%s:%s' %(len(a),a)
        elif type(a) is int:
            s+='i%ds' %(a)
        else:
            raise TypeError("Argument '%s', type '%s' cannot be encoded" %(a,type(a)))
    return s



class TelldusInFactory(ReconnectingClientFactory):
    noisy = False
    maxDelay = 10
    #factor=1.6180339887498948

    def __init__(self, protocol, parent):
        self.protocol = protocol
        self.parent = parent
        self.system = protocol.system

    def buildProtocol(self, addr):
        self.resetDelay()
        return self.protocol

    def clientConnectionLost(self, connector, reason):
        log(reason.getErrorMessage(), system=self.system)
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        log(reason.getErrorMessage(), system=self.system)
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
        self.protocol.state.set_ERROR(self.protocol.path,reason.getErrorMessage())


# STATE FLOW:
#                  ,--<------------------.
#    init -> starting -> ready -> up     |
#             |           ^  `--+-'      |
#             |           |     v        |
#             `-> error -'    down >-----'
#
class TelldusIn(Protocol):
    ''' Class for incoming Telldus events '''

    noisy = False
    path = '/tmp/TelldusEvents'


    def __init__(self,parent):
        self.parent = parent
        self.system = parent.system + '/in'
        self.state = State('init', system=self.system,
                            change_callback=lambda *a:self.parent.changestate(self,*a) )
        self.factory = TelldusInFactory(self, self.parent)


    def connect(self):
        self.state.set_STARTING()
        reactor.connectUNIX(self.path, self.factory)


    def connectionMade(self):
        log("Connected to %s" %(self.path,), system=self.system)
        self.state.set_READY()
        self.data = ''
        self.elements = [ ]


    def connectionLost(self, reason):
        log("Lost connection with %s" %(self.path,), system=self.system)
        self.state.set_DOWN(reason.getErrorMessage())


    def disconnect(self):
        if self.state.is_in('ready','up'):
            self.transport.loseConnection()


    def dataReceived(self, data):
        lograwin(data, system=self.system)

        data = self.data + data

        # Interpret the data
        (elements, data) = parsestream(data)
        (events, elements) = parseelements(elements, system=self.system)

        # Save remaining data for next call (incomplete frame received)
        self.data = data
        self.elements = elements

        # At this point, we can consider the connection up
        self.state.set_UP()

        # Iterate over the received events
        for event in events:
            logdatain(event, system=self.system)
            self.parent.parse_event(event)



class TelldusOutFactory(ClientFactory):
    noisy = False

    def __init__(self, protocol, parent):
        self.protocol = protocol
        self.parent = parent
        self.system = protocol.system

    def buildProtocol(self, addr):
        return self.protocol

    def clientConnectionFailed(self, connector, reason):
        self.protocol.clientConnectionFailed(reason)



# STATE FLOW:
#                  ,--<-------------------.
#    init -> starting -> ready -> up -> idle
#             |    ^       ^
#             |    |       |
#             `-> error <-'
#
class TelldusOut(Protocol):
    ''' Class for outgoing Telldus commands '''

    noisy = False
    path = '/tmp/TelldusClient'
    timeout = 5


    # This object is connected when data is about to be sent and closed right after.
    # The normal flow is:
    #   command() -> send_next() -> connectionMade() -> dataReceived()
    #   -> disconnect() -> connectionLost() [ -> send_next() ... ]

    def __init__(self,parent):
        self.parent = parent
        self.system = parent.system + '/out'
        self.state = State('init', system=self.system,
                           change_callback=lambda *a:self.parent.changestate(self,*a))
        self.queue = []
        self.active = None
        self.factory = TelldusOutFactory(self, self.parent)


    def connectionMade(self):
        self.state.set_READY()
        self.send()


    def connectionLost(self, reason):
        if self.state.is_in('ready'):
            # Lost connection before we could get any reply back.
            self.state.set_ERROR(self.path,reason.getErrorMessage())
            (defer, self.defer) = (self.defer, None)
            defer.errback(LostConnectionException(reason.getErrorMessage()))
        else:
            self.state.set_IDLE(reason.getErrorMessage())
        self.send_next(proceed=True)


    def clientConnectionFailed(self, reason):
        self.state.set_ERROR(self.path,reason.getErrorMessage())
        (defer, self.defer) = (self.defer, None)
        defer.errback(NoConnectionException(reason.getErrorMessage()))
        self.send_next(proceed=True)


    def disconnect(self):
        if self.state.is_in('ready','up'):
            self.transport.loseConnection()


    def dataReceived(self, data):
        self.state.set_UP()
        lograwin(data, system=self.system)
        (elements, data) = parsestream(data)

        # FIXME: Is it correct to send element to the callback? ....yes
        (defer, self.defer) = (self.defer, None)
        defer.callback(elements)

        self.disconnect()
        #self.send_next()


    def command(self, cmd):
        d = Deferred()
        self.queue.append( (d,cmd,generate(cmd)) )
        utils.add_defer_timeout(d, self.timeout, self.timedout, d)

        # Send the next package
        self.send_next()
        return d


    def send(self):
        logdataout(self.data, system=self.system)
        self.transport.write(self.data)


    def send_next(self, proceed=False):
        if self.active and not proceed:
            return
        self.active = None
        self.defer = None
        if len(self.queue):
            (self.defer, self.active, self.data) = self.queue.pop(0)

            #if self.state.is_in('ready','up'):
            #    self.send()
            #else:

            # Next will be connectionMade() or clientConnectionFailed()
            self.state.set_STARTING()
            reactor.connectUNIX(self.path, self.factory)

        #else:
        #    self.disconnect()


    def timedout(self, defer):
        # The timeout response is to fail the request and proceed with the next command
        log("Command '%s' timed out" %(self.active,), system=self.system)
        self.disconnect()
        self.state.set_ERROR('Timeout')
        defer.errback(TimeoutException())
        self.send_next(proceed=True)



class Telldus(Leaf):
    name = 'TELLDUS'


    # --- Initialization
    def setup(self, main):
        Leaf.setup(self, main)
        self.inport = TelldusIn(self)
        self.outport = TelldusOut(self)
        self.state = State('init', system=self.system)
        self.inport.connect()

    def close(self):
        self.inport.disconnect()
        self.outport.disconnect()


    # --- Callbacks
    # FIXME: Implement overall state logic
    def changestate(self,cls,state,oldstate,*args):
        return
        #if cls == self.inport:
        #    if state == 'connected':
        #        self.event('connected')
        #    elif state == 'closed':
        #        self.event('disconnected',*args)
        #    elif state == 'error':
        #        self.event('error',*args)
        #elif cls == self.outport:
        #    if state == 'error':
        #        self.event('error',*args)


    # --- Commands
    #def ison(self):
    #    if self.inport.state.is_in('connected','active'):
    #        return True
    #    else:
    #        return False

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


        if cmd == 'TDSensorEvent':
            # Ignore sensor events as they are handles as raw device events
            return

        if cmd == 'TDDeviceEvent':
            # Ignore device events as they are handled as raw device events
            return

        elif cmd == 'TDRawDeviceEvent':

            args = parserawargs(event[1])

            if 'protocol' not in args:
                log("Missing protocol from %s, dropping event" %(cmd),
                        system=self.inport.system)
                return

            #if args['protocol'] != 'arctech':
            #    #log("Ignoring unknown protocol '%s' in '%s', dropping event" %(args['protocol'],cmd), system=self.inport.system)
            #    continue

            # Check for matches in eventlist
            if args['protocol'] == 'arctech':

                # Transform 'turnon' to 'on'.
                if 'method' in args:
                    args['method'] = args['method'].replace('turn','')

                # Traverse events list
                for (ev,d) in self.events.items():

                    # Ignore everything not an in device
                    if d['t'] not in ('in',):
                        continue

                    # Compare the following attributes
                    if not utils.cmp_dict(args, d, ('house', 'group', 'unit', 'method')):
                        continue

                    # Match found, process it as an event
                    self.event(ev)
                    return

            elif args['protocol'] == 'mandolyn' or args['protocol'] == 'fineoffset':

                # Traverse events list
                for (ev,d) in self.events.items():

                    # Only consider temp devices
                    if d['t'] not in ('temp', ):
                        continue

                    # Compare the following attributes
                    if not utils.cmp_dict(args, d, ('id', )):
                        continue

                    # Match found, process it as an event
                    if 'humidity' in args:
                        self.event(ev,('temp',args['temp']),('humidity',args['humidity']))
                    else:
                        self.event(ev,('temp',args['temp']))
                    return

                # Not interested in logging temp events we don't subscribe to
                return

        # Ignore the other events
        log("Ignoring '%s' %s" %(cmd,event[1:]), system=self.inport.system)


    # --- Interfaces
    def configure(self):

        # Baseline commands and events
        self.commands = {
            #'state' : lambda a : (self.inport.state.get(), self.outport.state.get()),
            #'ison'  : lambda a : self.ison(),
        }
        self.events = {}

        # Telldus operations
        ops = {
            'on'  : lambda a,i : self.turnOn(i),
            'off' : lambda a,i : self.turnOff(i),
            'dim' : lambda a,i : self.dim(i,int(a.args[0])),
        }

        # -- Helper functions
        def add_out(eq,oplist):
            ''' Add commands to an output device '''
            if '{op}' not in eq['name']:
                raise ConfigException("telldus_config:%s: %s type requires usage of '{op}' in name" %(eq['i'],eq['t']))

            for op in oplist:
                d=eq.copy()
                d['op'] = op
                d['name'] = name = d['name'].format(**d)
                if name in self.commands:
                    raise ConfigException("telldus_config:%s: Command '%s' already in list" %(d['i'],name))

                # The lambda syntax needs to be carefully set, due to late binding the op=op
                # syntax is very important to bind the variable in this context
                # http://docs.python-guide.org/en/latest/writing/gotchas/#late-binding-closures
                self.commands[name] = lambda a,op=op,i=int(d['id']): ops[op](a,i)

        def add_event(eq,**kw):
            d=eq.copy()
            d.update(**kw)
            d['name'] = name = d['name'].format(**d)
            if name in self.events:
                raise ConfigException("telldus_config:%s: Event '%s' already in list" %(d['i'],name))
            self.events[name] = d

        def add_in(eq):
            if '{method}' not in eq['name']:
                raise ConfigException("telldus_config:%s: %s type requires usage of '{op}' in name" %(eq['i'],eq['t']))

            # Get the unit span and ensure either unit or num_units is set
            u_first=eq.get('unit')
            num_units = 1
            if u_first is None:
                u_first = 1
                num_units=eq.get('num_units')
                if num_units is None:
                    raise ConfigException("telldus_config:%s: Missing unit or num_units" %(eq['i']))

            # Loop through all units and methods
            for unit in range(int(u_first),int(u_first)+int(num_units)):
                for method in ('on','off'):
                    add_event(eq, unit=str(unit), method=method)

        # -- Traverse list for equipment and add to either self.commands or self.events
        for i,_eq in enumerate(telldus_config):
            # Everything must be str
            eq = { k:str(v) for k,v in _eq.items() }
            eq['i'] = i+1
            t = eq.get('t')
            if t is None:
                raise ConfigException("telldus_config:%s: Missing type" %(i+1))
            if 'name' not in eq:
                raise ConfigException("telldus_config:%s: Missing name" %(i+1))

            if t == 'dimmer':
                add_out(eq,('on','off','dim'))
            elif t == 'switch':
                add_out(eq,('on','off'))
            elif t == 'in':
                add_in(eq)
            elif t == 'temp':
                add_event(eq)
            else:
                raise ConfigException("telldus_config:%s: Unknown telldus equipment type %s" %(i+1,t))


# FIXME: Implement ability to generate tellstick.conf from telldus_config


# Main plugin object class
PLUGIN = Telldus

# -*-python-*-
from __future__ import absolute_import

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory, Protocol, ReconnectingClientFactory
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall

from lumina.node import Node
from lumina.state import ColorState
from lumina.log import Logger
from lumina.exceptions import NoConnectionException, TimeoutException, ConfigException
from lumina import utils



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
        n = data.split(':', 1)
        l = int(n[0])
        return (n[1][:l], n[1][l:])
    elif data and data[0] == 'i':
        n = data.split('s', 1)
        l = int(n[0][1:])
        return (l, n[1])
    else:
        return (None, data)



def parsestream(data):
    ''' Parse self.data byte stream into list of elements in self.elements '''
    el = []

    # Split the raw data into list of objects (string or integer)
    while True:
        (element, data) = getnextelement(data)
        if element is None:
            return el, data
        el.append(element)



def parseelements(elements, log):
    ''' Parse elements into events '''
    events = []

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
            log.info("Unknown command '{c}', dropping {e}", c=cmd, e=elements)
            elements = []
            break

        l = cmdsize[cmd]

        if l > len(elements):
            # Does not got enough data for command. Stop and postpone processing
            log.info("Missing elements for command '{c}', "
                     "got {e}, needs {l} args.", c=cmd, e=elements, l=l)
            elements = []
            break

        l = cmdsize[cmd]
        args = elements[:l]
        elements = elements[l:]
        events.append([cmd] + args)

    return (events, elements)



def parserawargs(args):
    ''' Split the 'key1:data1;key2:data2;...' string syntax into a dictionary '''

    alist = args.split(';')
    adict = dict()
    for a in alist:
        if a:
            o = a.split(':')
            adict[o[0]] = o[1]
    return adict



def generate(args):
    ''' Encode args into telldus string encoding, which is '<LEN>:string' and 'i<NUM>s' for
        integer. '''
    s = ''
    for a in args:
        if isinstance(a, str):
            s += '%s:%s' %(len(a), a)
        elif isinstance(a, int):
            s += 'i%ds' %(a)
        else:
            raise TypeError("Argument '%s', type '%s' cannot be encoded" %(a, type(a)))
    return s



class TelldusInFactory(ReconnectingClientFactory):
    noisy = False
    maxDelay = 10
    #factor=1.6180339887498948

    def __init__(self, protocol, parent):
        self.protocol = protocol
        self.parent = parent
        self.log = protocol.log

    def buildProtocol(self, addr):
        self.resetDelay()
        return self.protocol

    def clientConnectionLost(self, connector, reason):
        # This is handled in TelldusIn.connectionLost(), and is present here
        # to handle reconnection.
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        self.log.error('Connect failed {p}: {e}', p=self.protocol.path, e=reason.getErrorMessage())
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
        self.protocol.status.set_RED('IN connection failed')



class TelldusIn(Protocol):
    ''' Class for incoming Telldus events '''

    noisy = False
    path = '/tmp/TelldusEvents'
    idleTimeout = 60


    def __init__(self, parent):
        self.log = Logger(namespace=parent.name+'/in')
        self.parent = parent
        self.status = ColorState(log=self.log, state_format={0:0}) # <-- a hack to avoid color
        self.status.add_callback(self.parent.update_status)
        self.connected = False
        self.factory = TelldusInFactory(self, self.parent)


    def connect(self):
        self.status.set_OFF()
        reactor.connectUNIX(self.path, self.factory)


    def connectionMade(self):
        self.log.info("Connected to {p}", p=self.path)
        self.connected = True
        self.status.set_YELLOW('IN connection made, waiting for data')
        self.data = ''
        self.elements = []
        self.timer = LoopingCall(self.dataTimeout)
        self.timer.start(self.idleTimeout, now=False)


    def connectionLost(self, reason):
        self.connected = False
        self.log.info("Lost connection with {p}: {e}", p=self.path, e=reason.getErrorMessage())
        self.status.set_OFF('IN connection closed')
        if self.timer.running:
            self.timer.stop()


    def disconnect(self):
        if self.connected:
            self.transport.loseConnection()


    def dataReceived(self, data):
        self.log.debug('', rawin=data)

        if self.timer.running:
            self.timer.reset()
        else:
            self.timer.start(self.idleTimeout, now=False)

        data = self.data + data

        # Interpret the data
        (elements, data) = parsestream(data)
        (events, elements) = parseelements(elements, log=self.log)

        # Save remaining data for next call (incomplete frame received)
        self.data = data
        self.elements = elements

        # At this point, we can consider the connection up
        self.status.set_GREEN()

        # Iterate over the received events
        for event in events:
            self.log.debug('', datain=event)
            self.parent.parse_event(event)


    def dataTimeout(self):
        self.timer.stop()
        self.log.info("No telldus activity. No connection?")
        self.status.set_YELLOW('No activity')



class TelldusOutFactory(ClientFactory):
    noisy = False

    def __init__(self, protocol, parent):
        self.protocol = protocol
        self.parent = parent
        self.log = protocol.log

    def buildProtocol(self, addr):
        return self.protocol

    def clientConnectionFailed(self, connector, reason):
        self.protocol.clientConnectionFailed(reason)



#
# The Telldus client protocol requires opening the a UNIX socket to the client address,
# write the command and close the connection when done.
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

    def __init__(self, parent):
        self.log = Logger(namespace=parent.name+'/out')
        self.parent = parent
        self.status = ColorState(log=self.log, state_format={0:0})  # <-- a hack to avoid color
        self.status.add_callback(self.parent.update_status)
        self.connected = False
        self.completed = False
        self.running = True
        self.queue = []
        self.active = None
        self.factory = TelldusOutFactory(self, self.parent)


    def connectionMade(self):
        if self.status.is_in('OFF'):
            self.status.set_YELLOW('OUT connection made')
        self.connected = True
        self.completed = False
        self.send()


    def connectionLost(self, reason):
        self.connected = False
        if not self.completed:
            # Lost connection before we could get any reply back.
            self.log.error("Lost connection {p}: {e}",
                           p=self.protocol.path, e=reason.getErrorMessage())
            self.status.set_RED('Lost OUT connection')
            (defer, self.defer) = (self.defer, None)
            defer.errback(NoConnectionException(reason.getErrorMessage()))
        self.completed = False
        if self.running:
            self.send_next(proceed=True)


    def clientConnectionFailed(self, reason):
        self.log.error('Connection failed {p}: {e}',
                       p=self.protocol.path, e=reason.getErrorMessage())
        self.status.set_RED('OUT connection failed')
        (defer, self.defer) = (self.defer, None)
        defer.errback(NoConnectionException(reason.getErrorMessage()))
        self.send_next(proceed=True)


    def disconnect(self):
        if self.connected:
            self.running = False
            self.transport.loseConnection()
        self.status.set_OFF('Done')


    def dataReceived(self, data):
        self.status.set_GREEN()
        self.log.debug('', rawin=data)
        (elements, data) = parsestream(data)

        # FIXME: Is it correct to send element to the callback? ....yes
        (defer, self.defer) = (self.defer, None)
        defer.callback(elements)

        self.completed = True
        self.transport.loseConnection()


    def command(self, cmd):
        defer = Deferred()
        self.queue.append((defer, cmd, generate(cmd)))
        utils.add_defer_timeout(defer, self.timeout, self.timedout, defer)

        # Send the next package
        self.send_next()
        return defer


    def send(self):
        self.log.debug('', dataout=self.data)
        self.transport.write(self.data)


    def send_next(self, proceed=False):
        if self.active and not proceed:
            return
        self.active = None
        self.defer = None
        if len(self.queue):
            (self.defer, self.active, self.data) = self.queue.pop(0)

            # Next will be connectionMade() or clientConnectionFailed()
            reactor.connectUNIX(self.path, self.factory)


    def timedout(self, defer):
        # The timeout response is to fail the request and proceed with the next command
        self.log.err("Command '{c}' timed out", c=self.active)
        self.disconnect()
        self.status.set_RED('Timeout')
        defer.errback(TimeoutException())
        self.send_next(proceed=True)



class Telldus(Node):
    ''' Plugin to communicate with wireless lighting equipment and sensors.
    '''

    CONFIG = {
        'config': dict(default=[], help='Telldus configuration', type=list),
        'double_protect': dict(default=1.0, help='Protection time to prevent double triggering', type=float),
    }


    # --- Initialization
    def setup(self, main):
        Node.setup(self, main)

        self.doubleprotect = main.config.get('double_protect', name=self.name)
        self.emitted = {}

        self.inport = TelldusIn(self)
        self.outport = TelldusOut(self)
        self.inport.connect()

    def close(self):
        Node.close(self)
        self.inport.disconnect()
        self.outport.disconnect()


    # --- Callbacks
    def update_status(self, status):
        (state, why) = ColorState.combine(self.inport.status, self.outport.status)
        why = ". ".join([s.why for s in [self.inport.status, self.outport.status] if s.why is not None])
        self.status.set(state, why)



    # --- Commands
    def turnOn(self, num):
        cmd = ('tdTurnOn', num)
        return self.outport.command(cmd)

    def turnOff(self, num):
        cmd = ('tdTurnOff', num)
        return self.outport.command(cmd)

    def dim(self, num, val):
        cmd = ('tdDim', num, val)
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
                self.inport.log.info("Missing protocol from {c}, dropping event", c=cmd)
                return

            #if args['protocol'] != 'arctech':
            #    #log("Ignoring unknown protocol '%s' in '%s', dropping event"
            #    #    %(args['protocol'], cmd), system=self.inport.system)
            #    continue

            # Check for matches in eventlist
            if args['protocol'] == 'arctech':

                # Transform 'turnon' to 'on'.
                if 'method' in args:
                    args['method'] = args['method'].replace('turn', '')

                # Traverse events list
                for (ev, d) in self.events.items():

                    # Ignore everything not an in device
                    if d['protocol'] not in ('arctech',):
                        continue

                    # Compare the following attributes
                    if not utils.cmp_dict(args, d, ('house', 'group', 'unit', 'method')):
                        continue

                    # Match found, process it as an event
                    self.emit(ev)
                    return


            elif args['protocol'] == 'sartano':

                # Traverse events list
                for (ev, d) in self.events.items():

                    # Ignore everything not this type
                    if d['protocol'] not in ('sartano',):
                        continue

                    # Compare the following attributes
                    if not utils.cmp_dict(args, d, ('code', )):
                        continue

                    # Match found, process it as an event
                    self.emit(ev)
                    return


            elif args['protocol'] in ('mandolyn', 'fineoffset', 'oregon'):

                # Traverse events list
                for (ev, d) in self.events.items():

                    # Only consider temp devices
                    if d['protocol'] not in ('temp', ):
                        continue

                    # Compare the following attributes
                    if not utils.cmp_dict(args, d, ('id', )):
                        continue

                    # Match found, process it as an event
                    if 'humidity' in args:
                        self.emit(ev, ('temp', args['temp']),
                                  ('humidity', args['humidity']))
                    else:
                        self.emit(ev, ('temp', args['temp']))
                    return

                # Uncommant if not interested in logging temp events we don't subscribe to
                return

        # Ignore the other events
        self.inport.log.info("Ignoring '{c}' {e}", c=cmd, e=event[1:])


    # --- Override default emit
    def emit(self, event, *args):
        self.inport.log.info("Event '{e}'", e=event)
        if event in self.emitted:
            self.inport.log.info("Event '{e}' double triggered", e=event)
            return

        # Prevent double-triggering of events by starting a timer. As long
        # as the timer runs, any additional events of the same type will
        # be filtered.
        def del_protect(event):
            del self.emitted[event]
        self.emitted[event] = True
        reactor.callLater(self.doubleprotect, del_protect, event)
        Node.emit(self, event, *args)


    # --- Interfaces
    def configure(self, main):

        # Baseline commands and events
        self.commands = {}
        self.events = {}

        # Telldus operations
        ops = {
            'on'  : lambda a, i: self.turnOn(i),
            'off' : lambda a, i: self.turnOff(i),
            'dim' : lambda a, i: self.dim(i, int(a.args[0])),
        }

        # -- Helper functions
        def add_out(eq, oplist):
            ''' Add commands to an output device '''
            if '{op}' not in eq['name']:
                raise ConfigException("telldus_config:%s: "
                                      "%s protocol requires usage of '{op}' in name"
                                      %(eq['i'], eq['protocol']))

            for op in oplist:
                d = eq.copy()
                d['op'] = op
                d['name'] = name = d['name'].format(**d)
                if name in self.commands:
                    raise ConfigException("telldus_config:%s: "
                                          "Command '%s' already in list"
                                          %(d['i'], name))

                # The lambda syntax needs to be carefully set, due to late binding the op=op
                # syntax is very important to bind the variable in this context
                # http://docs.python-guide.org/en/latest/writing/gotchas/#late-binding-closures
                self.commands[name] = lambda a, op=op, i=int(d['id']): ops[op](a, i)

        def add_event(eq, **kw):
            d = eq.copy()
            d.update(**kw)
            d['name'] = name = d['name'].format(**d)
            #if name in self.events:
            #    raise ConfigException("telldus_config:%s: "
            #                          "Event '%s' already in list"
            #                          %(d['i'], name))
            self.events[name] = d

        def add_arctech(eq):

            # Get the unit span and ensure either unit or num_units is set
            u_first = eq.get('unit')
            num_units = 1
            if u_first is None:
                u_first = 1
                num_units = eq.get('num_units')
                if num_units is None:
                    raise ConfigException("telldus_config:%s: "
                                          "Missing unit or num_units"
                                          %(eq['i']))

            # Loop through all units and methods
            for unit in range(int(u_first), int(u_first)+int(num_units)):
                if '{method}' in eq['name']:
                    for method in ('on', 'off'):
                        add_event(eq, unit=str(unit), method=method)
                else:
                    add_event(eq, unit=str(unit))


        # -- Traverse list for equipment and add to either self.commands or self.events
        telldus_config = main.config.get('config', name=self.name)
        for i, rconfig in enumerate(telldus_config):
            # Everything must be str
            eq = {k:str(v) for k, v in rconfig.items()}
            eq['i'] = i+1
            t = eq.get('protocol')
            if t is None:
                raise ConfigException("telldus_config:%s: "
                                      "Missing protocol"
                                      %(i+1))
            if 'name' not in eq:
                raise ConfigException("telldus_config:%s: "
                                      "Missing name"
                                      %(i+1))

            if t == 'dimmer':
                add_out(eq, ('on', 'off', 'dim'))
            elif t == 'switch':
                add_out(eq, ('on', 'off'))
            elif t == 'arctech':
                add_arctech(eq)
            elif t == 'temp':
                add_event(eq)
            elif t == 'sartano':
                add_event(eq)
            else:
                raise ConfigException("telldus_config:%s: "
                                      "Unknown telldus equipment protocol %s"
                                      %(i+1, t))


# FIXME: Implement ability to generate tellstick.conf from telldus_config


# Main plugin object class
PLUGIN = Telldus

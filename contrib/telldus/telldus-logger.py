#!/usr/bin/env python
#
# Tool to log events from Telldus into Graphite
#

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory, Protocol, ReconnectingClientFactory
from twisted.logger import Logger, textFileLogObserver
from twisted.logger import ILogObserver, formatEventAsClassicLogText
from twisted.logger import globalLogPublisher, globalLogBeginner
from twisted.python.syslog import SyslogObserver
from zope.interface import implementer
from twisted.internet.task import LoopingCall
from twisted.internet.error import ConnectionDone
import pickle
import time
import struct
import sys
import setproctitle


# Settings
graphite_host = 'hus.local'
graphite_port = 2004

# Temperature devices
temp_devices = [
    { "type": "temp", "id": '11',  "name": "huset.ute" },
    { "type": "temp", "id": '12',  "name": "huset.kjeller"  },
    { "type": "temp", "id": '247', "name": "huset.fryseskap"  },
    { "type": "temp", "id": '135', "name": "huset.kino_ute"  },
    { "type": "temp", "id": '151', "name": "huset.kino_inne"  },
]

# Cache to store latest readings
temp_cache = {}


#
# Logging services
#
@implementer(ILogObserver)
class MyLogObserver(object):
    def __call__(self, event):
        text = event['log_format'].format(**event)
        sys.stdout.write(text + '\n')
        sys.stdout.flush()

#globalLogBeginner.beginLoggingTo([textFileLogObserver(sys.stdout)])
#globalLogBeginner.beginLoggingTo([LegacySyslogObserver('telldus-logger')])
#globalLogBeginner.beginLoggingTo([MyLogObserver()])
globalLogPublisher.addObserver(MyLogObserver())

log = Logger()
log.info("Starting logging")



class GraphiteProtocol(Protocol):
    noisy = False

    def __init__(self, name, readings):
        self.msg = self.compile_msg(name, readings)
        log.info("Sending {n}: {v}", n=name, v=readings)


    def compile_msg(self, name, readings):

        # Some sensors have a tendency to glitch. So if the temp difference
        # from the last reading is >20 degrees, then this reading is a glitch
        val = float(readings[0][1])
        last = temp_cache.get(name, None)
        if last is not None and abs(val-last) > 20:
            log.info("Ignoring {n} temperature of {v} (last {l})", n=name, v=val, l=last)
            return
        temp_cache[name] = val

        t = time.time()
        l = []
        for v in readings:
            l += [( name+'.'+v[0], (t, v[1]) )]
        payload = pickle.dumps(l, protocol=2)
        header = struct.pack("!L", len(payload))
        return header + payload


    def connectionMade(self):
        self.transport.write(self.msg)
        self.transport.loseConnection()



class GraphiteFactory(ClientFactory):
    noisy = False

    def __init__(self, name, readings):
        self.protocol = GraphiteProtocol(name, readings)
        reactor.connectTCP(graphite_host, graphite_port, self)

    def buildProtocol(self, addr):
        return self.protocol

    def clientConnectionFailed(self, connector, reason):
        log.info('Graphite connect failed {h}:{p}: {e}', h=graphite_host, p=graphite_port,
                 e=reason.getErrorMessage())

    def clientConnectionLost(self, connector, reason):
        if not isinstance(reason.value, ConnectionDone):
            log.info('Graphite connection lost {h}:{p}: {e}', h=graphite_host, p=graphite_port,
                 e=reason.getErrorMessage())



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


def parseelements(elements):
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


class TelldusIn(Protocol):
    ''' Class for incoming Telldus events '''

    noisy = False


    def connectionMade(self):
        log.info("Connected to Telldus")
        self.data = ''
        self.elements = []


    def dataReceived(self, data):

        data = self.data + data

        # Interpret the data
        (elements, data) = parsestream(data)
        (events, elements) = parseelements(elements)

        # Save remaining data for next call (incomplete frame received)
        self.data = data
        self.elements = elements

        # Iterate over the received events
        for event in events:
            self.parse_event(event)


    # --- Event filter
    def parse_event(self, event):
        cmd = event[0]

        log.info("TD {e}", e=event)

        #if cmd == 'TDSensorEvent':
        #    # Ignore sensor events as they are handles as raw device events
        #    return

        #if cmd == 'TDDeviceEvent':
        #    # Ignore device events as they are handled as raw device events
        #    return

        if cmd == 'TDRawDeviceEvent':

            args = parserawargs(event[1])

            #if 'protocol' not in args:
            #    self.inport.log.info("Missing protocol from {c}, dropping event", c=cmd)
            #    return

            #if args['protocol'] != 'arctech':
            #    #log("Ignoring unknown protocol '%s' in '%s', dropping event"
            #    #    %(args['protocol'], cmd), system=self.inport.system)
            #    continue

            # Check for matches in eventlist
            #if args['protocol'] == 'arctech':

            #    # Transform 'turnon' to 'on'.
            #    if 'method' in args:
            #        args['method'] = args['method'].replace('turn', '')

            #    # Traverse events list
            #    for (ev, d) in self.events.items():

            #        # Ignore everything not an in device
            #        if d['type'] not in ('in',):
            #            continue

            #        # Compare the following attributes
            #        if not utils.cmp_dict(args, d, ('house', 'group', 'unit', 'method')):
            #            continue

            #        # Match found, process it as an event
            #        self.emit(ev)
            #        return

            if args['protocol'] == 'mandolyn' or args['protocol'] == 'fineoffset':

                # Traverse events list
                for d in temp_devices:

                    # Only consider temp devices
                    if d['type'] not in ('temp', ):
                        continue

                    if 'id' not in args or 'id' not in d:
                        continue

                    if d['id'] != args['id']:
                        continue

                    # Match found, send it to Graphite
                    if 'humidity' in args:
                        GraphiteFactory(d['name'],
                                        (('temp', args['temp']),
                                         ('humidity', args['humidity'])))
                    else:
                        GraphiteFactory(d['name'],
                                        (('temp', args['temp']),))
                    return


class TelldusInFactory(ReconnectingClientFactory):
    noisy = False
    maxDelay = 10
    #factor=1.6180339887498948
    path = '/tmp/TelldusEvents'

    def __init__(self):
        reactor.connectUNIX(self.path, self)
        log.info("Connecting to {p}...", p=self.path)

    def buildProtocol(self, addr):
        self.resetDelay()
        return TelldusIn()

    def clientConnectionLost(self, connector, reason):
        log.info("TD Connection lost {p}: {e}", p=self.path, e=reason.getErrorMessage())
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        log.info("TD Connection failed {p}: {e}", p=self.path, e=reason.getErrorMessage())
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)



#==  SET PROC TITLE
setproctitle.setproctitle('telldus-logger')
TelldusInFactory()
reactor.run()

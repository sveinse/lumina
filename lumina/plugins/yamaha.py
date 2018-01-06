# -*-python-*-
""" Yamaha Aventage AV Receiver interface plugin """
from __future__ import absolute_import, division, print_function

import re
from Queue import Queue
import xml.etree.ElementTree as ET
import socket

from twisted.internet.defer import Deferred
from twisted.internet.protocol import DatagramProtocol, ClientFactory, Protocol
#from twisted.web.client import Agent
#from twisted.web.http_headers import Headers

from lumina.node import Node
from lumina.log import Logger
from lumina.exceptions import LuminaException, CommandRunException, TimeoutException


class SSDPException(LuminaException):
    pass


GET = 'GET'
PUT = 'PUT'

ROOT = 'YAMAHA_AV'

XML_RC_ERRORS = {
    0: 'OK',
    1: 'Reserved command used',
    2: 'Error in node designation',
    3: 'Error in parameter (value/range)',
    4: 'Not successfully set due to a system error',
    5: 'Internal error',
}

POWER_ALL = ('System', 'Power_Control', 'Power')
POWER_MAIN = ('Main_Zone', 'Power_Control', 'Power')
VOLUME = ('Main_Zone', 'Volume', 'Lvl')
INPUT = ('Main_Zone', 'Input', 'Input_Sel')
PURE_DIRECT = ('Main_Zone', 'Sound_Video', 'Pure_Direct', 'Mode')
MUTE = ('Main_Zone', 'Volume', 'Mute')   # Parameter On Off On/Off 'Att -20 dB'

SPEAKER_LEVELS1 = ('System', 'Speaker_Preout', 'Pattern_1', 'Lvl')
SPEAKER_LEVELS2 = ('System', 'Speaker_Preout', 'Pattern_2', 'Lvl')
SPEAKER_DISTANCE1 = ('System', 'Speaker_Preout', 'Pattern_1', 'Distance')
SPEAKER_DISTANCE2 = ('System', 'Speaker_Preout', 'Pattern_2', 'Distance')
SPEAKER_PEQ1 = ('System', 'Speaker_Preout', 'Pattern_1', 'PEQ', 'Manual_Data')
SPEAKER_PEQ2 = ('System', 'Speaker_Preout', 'Pattern_2', 'PEQ', 'Manual_Data')


def dB(value):
    return {'Val': int(float(value)*10),
            'Exp': 1,
            'Unit': 'dB'}
def dB_t(text):
    return {'Val': text,
            'Exp': '',
            'Unit': ''}
def parse_dB(xml):
    # <Val>20</Val><Exp>1</Exp><Unit>dB</Unit>
    return float(xml.find('Val').text) * 10 ** (-float(xml.find('Exp').text))

def parse_val(xml):
    return float(xml.find('Val').text) * 10 ** (-float(xml.find('Exp').text))

def meter(value):
    return {'Val': int(float(value)*100),
            'Exp': 2,
            'Unit': 'm'}

def parse_levels(xml):
    # <YAMAHA_AV rsp="GET" RC="0"><System><Speaker_Preout><Pattern_1><Lvl>
    # <Front_L><Val>20</Val><Exp>1</Exp><Unit>dB</Unit></Front_L>
    channels = {}
    for ch in xml:
        channels[ch.tag] = parse_dB(ch)
    return channels

def parse_distance(xml):
    # <YAMAHA_AV rsp="GET" RC="0"><System><Speaker_Preout><Pattern_1><Distance>
    # <Unit_of_Distance>Meter</Unit_of_Distance>
    # <Meter><Front_L><Val>280</Val><Exp>2</Exp><Unit>m</Unit></Front_L>
    meter = xml.find('Meter')
    channels = {}
    for ch in meter:
        channels[ch.tag] = parse_val(ch)
    return channels

def parse_peq(xml):
    # <YAMAHA_AV rsp="GET" RC="0"><System><Speaker_Preout><Pattern_1><PEQ><Manual_Data><Front_L>
    #   <Band_1><Freq>125.0 Hz</Freq><Gain><Val>20</Val><Exp>1</Exp><Unit>dB</Unit></Gain><Q>0.630</Q></Band_1>
    bands = []
    for band in xml:
        bands.append({'freq': band.find('Freq').text,
                      'gain': parse_val(band.find('Gain')),
                      'q': float(band.find('Q').text),
                     })
    return bands

def t(xml):
    return xml.text

def ison(xml):
    if xml.text == 'On':
        return True
    else:
        return False


class YamahaSSDP(DatagramProtocol):
    noisy = False
    system = 'AVR'

    def __init__(self, parent, host, group):
        self.log = Logger(namespace=parent.name+'/ssdp')
        self.parent = parent
        self.status = parent.status
        self.host = socket.gethostbyname(host)
        self.group = group


    def startProtocol(self):
        self.transport.setTTL(2)
        self.transport.joinGroup(self.group)


    def disconnect(self):
        if self.transport:
            self.transport.loseConnection()


    def datagramReceived(self, datagram, address):
        if address[0] != self.host:
            return

        #self.log.debug("Datagram {d} received from {a}", d=repr(datagram), a=repr(address))

        # Skip the header (which is HTTP like), and extract the body
        header = True
        body = ''
        for line in datagram.split('\r\n'):
            if header:
                if len(line) == 0:
                    header = False
            else:
                body += line

        # Ignore empty notifications
        if len(body) == 0:
            #self.log.info("Ignoring empty notifications")
            return

        #self.log.info("Received '{b}' from {a}", b=body, a=repr(address))

        # Convert to XML
        try:
            xml = ET.fromstring(body)
            if xml.tag != ROOT:
                raise SSDPException("'%s' is not root" %(ROOT,))

            mz = xml.find('Main_Zone')
            if mz is not None:
                notifications = [prop.text for prop in mz.iter('Property')]
                #self.log.info("Notification: {n}", n=notifications)
                self.parent.notification(notifications)

        except (ET.ParseError, SSDPException) as e:
            self.log.info("Malformed notification XML, {m}. XML='{b}'", m=e.message, b=body)
            return



class YamahaFactory(ClientFactory):
    noisy = False

    def __init__(self, protocol, parent):
        self.log = protocol.log
        self.protocol = protocol
        self.parent = parent

    def buildProtocol(self, addr):
        return self.protocol

    def clientConnectionFailed(self, connector, reason):
        self.protocol.clientConnectionFailed(reason)



class YamahaProtocol(Protocol):
    noisy = False
    timeout = 5

    def __init__(self, parent, host, port):
        self.log = Logger(namespace=parent.name+'/main')
        self.parent = parent
        self.master = parent.master
        self.status = parent.status
        self.host = host
        self.port = port
        self.queue = Queue()
        self.factory = YamahaFactory(self, self.parent)

        self.re_http = re.compile(r'HTTP/\S+ (\d+) (.*)')
        self.re_header = re.compile(r'\s*(\S+)\s*:\s*(.*)\s*')

        self.defer = None


    def connectionMade(self):
        self.log.info("Connection made")
        body = self.lastbody
        myip = self.transport.getHost().host
        data = '''POST /YamahaRemoteControl/ctrl HTTP/1.1\r
Host: %s\r
Content-Type: text/xml; charset="utf-8"\r
Content-Length: %s\r
Connection: keep-alive\r
\r
%s''' %(myip, len(body), body)
        #log.msg( "     <<<  %s" %(self.queue.active['chain']), system=self.system)
        self.log.debug("     <<<  '{b}'", b=body)
        #log.msg("RAW  <<<  (%s)'%s'" %(len(data),data), system=self.system)
        self.data = ''
        self.dstate = 'http'
        self.length = 0
        self.header = {}
        self.transport.write(data)


    def connectionLost(self, reason):  # pylint: disable=W0222
        self.log.info("Connection lost: {e}", e=reason.getErrorMessage())
        #self.setstate('closed', reason.getErrorMessage())
        # This will catch up server-side close and 0 length body packages
        if self.dstate != 'done':
            self.slurp_body()


    def clientConnectionFailed(self, reason):
        self.log.info("Connection failed: {e}", e=reason.getErrorMessage())


    def disconnect(self):
        #if self.state in ('connected','active'):
        if self.transport:
            self.transport.loseConnection()


    def dataReceived(self, data):
        #self.setstate('active')
        self.data += data
        self.log.debug("RAW  >>>  ({l})'{d}'", l=len(data), d=data)

        # Body part of the frame
        if self.dstate == 'body':
            self.slurp_body()
            return

        while True:
            # Get the next line and exit the loop if no more lines found
            pat = '\r\n'
            sub = self.data.find(pat)
            if sub < 0:
                return
            line = self.data[0:sub]
            self.data = self.data[sub+len(pat)::]

            # First line (HTML protocol)
            if self.dstate == 'http':
                m = self.re_http.search(line)
                if not m:
                    raise Exception("Malformed HTTP header")
                self.httperr = int(m.group(1))
                self.httptxt = m.group(2)
                self.dstate = 'header'

            # Header
            elif self.dstate == 'header':
                if len(line) == 0:
                    self.dstate = 'body'
                    self.length = int(self.header['Content-Length'])
                    self.slurp_body()
                else:
                    m = self.re_header.search(line)
                    if not m:
                        raise Exception("Malformed HTML header")
                    self.header[m.group(1)] = m.group(2)


    def slurp_body(self):

        # Enough data?
        if not len(self.data) or len(self.data) < self.length:
            return
        body = self.data[0:self.length]
        self.dstate = 'done'

        # Got what we want, so let's close the connection
        self.disconnect()

        try:
            # Check http error code
            if self.httperr == 400:
                raise CommandRunException('HTML err %s, Bad request, XML Parse error' %(self.httperr,))

            self.log.debug("     >>>  '{b}'", b=body)
            xml = ET.fromstring(body)
            if xml.tag != ROOT:
                raise CommandRunException("'%s' is XML root, not '%s'" %(xml.tag, ROOT))

            # Response to our object?
            rsp = xml.attrib['rsp']
            command = self.lastcommand
            if rsp != command:
                raise CommandRunException("Response is '%s', command was '%s'" %(rsp, command))

            # Check the return code in the top xml object
            rc = int(xml.attrib['RC'])
            err = XML_RC_ERRORS.get(rc, None)
            if err is None:
                raise CommandRunException("Unknown response, %s, from Yamaha" %(rc,))
            if err != 'OK':
                raise CommandRunException(err)

            # Unwind the chain
            chain = self.lastchain
            xmle = xml
            for c in chain:
                sub = xmle.find(c)
                if sub is None:
                    raise CommandRunException("Response XML does not match request on level '%s'" %(c,))
                xmle = sub

            #log.msg("     >>>  '%s'" %(ET.tostring(xmle),), system=self.system)

            if command == PUT:
                self.parent.status.set_GREEN()
                self.defer.callback(xmle.text)
            else:
                self.parent.status.set_GREEN()
                self.defer.callback(xmle)

        except (ET.ParseError, CommandRunException) as e:
            self.log.info("Command failed. {m}.", m=e.message)
            self.defer.errback(e)

        # Process next command
        self.timer.cancel()
        self.defer = None
        self.send_next()


    def command(self, command, chain, data=None):
        # Compile an XML request
        xml = ET.Element(ROOT, attrib={'cmd': command})
        xmle = xml
        for c in chain:
            xmle = ET.SubElement(xmle, c)
        if command == GET:
            xmle.text = 'GetParam'
        elif command == PUT:
            if isinstance(data, dict):
                for (k, v) in data.items():
                    ET.SubElement(xmle, k).text = str(v)
            else:
                xmle.text = str(data)

        body = ET.tostring(xml, encoding='utf-8')

        defer = Deferred()
        self.queue.put((defer, command, chain, body))
        self.send_next()
        return defer


    def send_next(self):

        # Don't send new if communication is pending
        if self.defer:
            return

        while self.queue.qsize():
            (defer, command, chain, body) = self.queue.get(False)

            # Send the command
            self.master.reactor.connectTCP(self.host, self.port, self.factory)

            # Expect reply
            self.lastcommand = command
            self.lastchain = chain
            self.lastbody = body
            self.defer = defer
            self.timer = self.master.reactor.callLater(self.timeout, self.timedout)
            return


    def timedout(self):
        # The timeout response is to fail the request and proceed with the next command
        self.log.info("Communication timed out.")
        self.status.set_RED('Timeout')
        self.defer.errback(TimeoutException())
        self.send_next()



class Yamaha(Node):
    ''' Yamaha Aventage AVR interface
    '''

    CONFIG = {
        'host'     : dict(default='localhost', help='Yamaha host'),
        'port'     : dict(default=80, help='Yamaha port', type=int),
        'ssdp'     : dict(default='239.255.255.250', help='Yamaha SSDP protocol address'),
        'ssdp_port': dict(default=1900, help='Yamaha SSDP port', type=int),
    }

    # --- Interfaces
    def configure(self):

        self.events = (
            #'avr/starting',      # Created avr object
            #'avr/stopping',      # close() have been called
            #'avr/error',         # Connection failed

            #'avr/volume',        # Volume event
            #'avr/input',         # Input change event
            #'avr/power',         # Change in power
        )

        self.commands = {
            'ison'        : lambda a: self.c(GET, POWER_ALL).addCallback(ison),
            'on'          : lambda a: self.c(PUT, POWER_MAIN, 'On'),
            'off'         : lambda a: self.c(PUT, POWER_ALL, 'Standby'),
            'pure_direct' : lambda a: self.c(PUT, PURE_DIRECT, 'On'),
            'input'       : lambda a: self.c(PUT, INPUT, a.args[0]),
            'volume'      : lambda a: self.c(PUT, VOLUME, dB(a.args[0])),
            'mute'        : lambda a: self.c(PUT, MUTE, 'On/Off'),

            #'avr/raw'         : lambda a : self.protocol.command(*a.args),
            #'avr/ison'        : lambda a : self.c(GET, POWER).addCallback(ison),
            #'avr/volume'      : lambda a : self.c(GET, VOLUME).addCallback(parse_dB),
            #'avr/volume/up'   : lambda a : self.c(PUT, VOLUME, dB_t('Up')),
            #'avr/volume/down' : lambda a : self.c(PUT, VOLUME, dB_t('Down')),
            #'avr/input'       : lambda a : self.c(GET, INPUT).addCallback(t),

            # YPAO settings
            'speaker/levels/1'   : lambda a: self.c(GET, SPEAKER_LEVELS1).addCallback(parse_levels),
            'speaker/levels/2'   : lambda a: self.c(GET, SPEAKER_LEVELS2).addCallback(parse_levels),
            'speaker/distance/1' : lambda a: self.c(GET, SPEAKER_DISTANCE1).addCallback(parse_distance),
            'speaker/distance/2' : lambda a: self.c(GET, SPEAKER_DISTANCE2).addCallback(parse_distance),

            # FIXME: These don't work as SPEAKER_PEQ is tuple
            #'speaker/peq/1'      : lambda a: self.c(GET, SPEAKER_PEQ1 + [ a.args[0] ]).addCallback(parse_peq),
            #'speaker/peq/2'      : lambda a: self.c(GET, SPEAKER_PEQ2 + [ a.args[0] ]).addCallback(parse_peq),
       }


    # --- Initialization
    def setup(self):

        self.host = self.master.config.get('host', name=self.name)
        self.port = self.master.config.get('port', name=self.name)
        self.ssdp_host = self.master.config.get('ssdp', name=self.name)
        self.ssdp_port = self.master.config.get('ssdp_port', name=self.name)

        self.protocol = YamahaProtocol(self, self.host, self.port)
        self.ssdp = YamahaSSDP(self, self.host, self.ssdp_host)

        self.master.reactor.listenMulticast(self.ssdp_port, self.ssdp, listenMultiple=True)

        # Send a dummy command to force connection to the device. This will
        # put it in GREEN or RED mode.
        self.commands['ison'](None)


    def close(self):
        Node.close(self)
        self.protocol.disconnect()
        self.ssdp.disconnect()


    # --- Convenience
    def c(self, *args, **kw):
        return self.protocol.command(*args, **kw)


    # --- Callbacks
    def notification(self, notifications):
        self.status.set_GREEN()
        self.log.info("Got notifications: {n}", n=notifications)
        #if 'Volume' in notifications:
        #    self.get_command('avr/volume')(None).addCallback(self.event_as_arg, 'avr/volume')
        #if 'Input' in notifications:
        #    self.get_command('avr/input')(None).addCallback(self.event_as_arg, 'avr/input')
        #if 'Power' in notifications:
        #    self.get_command('avr/ison')(None).addCallback(self.event_as_arg, 'avr/ison')



PLUGIN = Yamaha

# -*-python-*-
import os,sys,re
import traceback

from twisted.internet import reactor
from twisted.python import log
from twisted.internet.protocol import DatagramProtocol, ClientFactory, Protocol
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
import xml.etree.ElementTree as ET

from endpoint import Endpoint
from queue import Queue
from exceptions import *


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

POWER = [ 'System', 'Power_Control', 'Power' ]
VOLUME = [ 'Main_Zone', 'Volume', 'Lvl' ]
INPUT = [ 'Main_Zone', 'Input', 'Input_Sel' ]

PATTERN2_FRONTL = [ 'System', 'Speaker_Preout', 'Pattern_2', 'PEQ', 'Manual_Data', 'Front_L' ]


def dB(value):
    return { 'Val': int(float(value)*10),
             'Exp': 1,
             'Unit': 'dB' }

def parse_dB(xml):
    return float(xml.find('Val').text) * 10 ** (-float(xml.find('Exp').text))

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
        self.parent = parent
        self.host = host
        self.group = group


    def startProtocol(self):
        self.transport.setTTL(2)
        self.transport.joinGroup(self.group)


    def disconnect(self):
        self.transport.loseConnection()


    def datagramReceived(self, datagram, address):
        if address[0] != self.host:
            return

        #log.msg("Datagram %s received from %s" % (repr(datagram), repr(address)), system=self.system)

        # Skip the header (which is HTTP like), and extract the body
        header=True
        body=''
        for line in datagram.split('\r\n'):
            if header:
                if len(line) == 0:
                    header=False
            else:
                body += line

        # Ignore empty notifications
        if len(body)==0:
            #log.msg("Ignoring empty notifications", system=self.system)
            return

        #log.msg("Received '%s' from %s" % (body, repr(address)), system=self.system)

        # Convert to XML
        try:
            xml = ET.fromstring(body)
            if xml.tag != ROOT:
                raise SSDPException("'%s' is not root" %(ROOT,))

            mz = xml.find('Main_Zone')
            if mz is not None:
                notifications = [ prop.text for prop in mz.iter('Property') ]
                log.msg("AVR notification: %s" %(notifications,), system=self.system)
                self.parent.notification(notifications)

        except (ET.ParseError, SSDPException) as e:
            log.msg("Malformed XML, %s. XML='%s'" %(e.message,body), system=self.system)
            return



class YamahaFactory(ClientFactory):
    noisy = False

    def __init__(self, protocol, parent):
        self.protocol = protocol
        self.parent = parent

    def buildProtocol(self, addr):
        return self.protocol

    def clientConnectionFailed(self, connector, reason):
        self.protocol.setstate('error',self.protocol.path,reason.getErrorMessage())



class YamahaProtocol(Protocol):
    noisy = False
    timeout = 5
    system = 'AVR'

    def __init__(self,parent,host,port):
        self.state = 'init'
        self.parent = parent
        self.host = host
        self.port = port
        self.queue = Queue()
        self.factory = YamahaFactory(self, self.parent)

        self.re_http = re.compile('HTTP/\S+ (\d+) (.*)')
        self.re_header = re.compile('\s*(\S+)\s*:\s*(.*)\s*')


    def setstate(self,state,*args):
        (old, self.state) = (self.state, state)
        if state != old:
            log.msg("STATE change: '%s' --> '%s'" %(old,state), system=self.system)


    def connectionMade(self):
        self.setstate('connected')
        body = self.queue.active['body']
        myip = self.transport.getHost().host
        data = 'POST /YamahaRemoteControl/ctrl HTTP/1.1\r\nHost: %s\r\nContent-Type: text/html; charset="utf-8"\r\nContent-Length: %s\r\n\r\n%s' %(myip,len(body),body)
        log.msg( "     <<<  %s" %(self.queue.active['chain']), system=self.system)
        #log.msg( "     <<<  '%s'" %(body,), system=self.system)
        #log.msg("RAW  <<<  (%s)'%s'" %(len(data),data), system=self.system)
        self.data = ''
        self.dstate = 'http'
        self.length = 0
        self.header = {}
        self.transport.write(data)


    def connectionLost(self, reason):
        self.setstate('closed', reason.getErrorMessage())
        # This will catch up server-side close and 0 length body packages
        if self.dstate != 'done':
            self.slurp_body()


    def disconnect(self):
        if self.state in ('connected','active'):
            self.transport.loseConnection()


    def dataReceived(self, data):
        self.setstate('active')
        self.data += data
        #log.msg("RAW  >>>  (%s)'%s'" %(len(data),data), system=self.system)

        # Body part of the frame
        if self.dstate == 'body':
            self.slurp_body()
            return

        while True:
            # Get the next line and exit the loop if no more lines found
            pat = '\r\n'
            sub = self.data.find(pat)
            if sub<0:
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
                    self.header[m.group(1)]=m.group(2)


    def slurp_body(self):

        # Enough data?
        if len(self.data) < self.length:
            return
        body = self.data[0:self.length]
        self.dstate = 'done'

        # Got what we want, so let's close the connection
        self.disconnect()

        try:
            # Check http error code
            if self.httperr == 400:
                raise CommandFailedException('HTML err %s, Bad request, XML Parse error' %(self.httperr,))

            #log.msg( "     >>>  '%s'" %(body,), system=self.system)
            xml = ET.fromstring(body)
            if xml.tag != ROOT:
                raise CommandFailedException("'%s' is XML root, not '%s'" %(xml.tag,ROOT))

            # Response to our object?
            rsp = xml.attrib['rsp']
            cmd = self.queue.active['cmd']
            if rsp != cmd:
                raise CommandFailedException("Response is '%s', command was '%s'" %(rsp, cmd))

            # Check the return code in the top xml object
            rc = int(xml.attrib['RC'])
            err = XML_RC_ERRORS.get(rc, None)
            if err is None:
                raise CommandFailedException("Unknown response, %s, from Yamaha" %(rc,))
            if err != 'OK':
                raise CommandFailedException(err)

            # Unwind the chain
            chain = self.queue.active['chain']
            xe = xml
            for c in chain:
                sub = xe.find(c)
                if sub is None:
                    raise CommandFailedException("Response XML does not match request on level '%s'" %(c,))
                xe = sub

            log.msg("     >>>  '%s'" %(ET.tostring(xe),), system=self.system)

            if cmd == PUT:
                self.queue.callback(xe.text)
            else:
                self.queue.callback(xe)

        except (ET.ParseError, CommandFailedException) as e:
            log.msg("Command failed. %s." %(e.message,), system=self.system)
            self.queue.errback(e)

        # Process next command
        self.send_next()


    def command(self, cmd, chain, data=None):
        # Compile an XML request
        xml = ET.Element(ROOT, attrib={ 'cmd': cmd})
        xe = xml
        for c in chain:
            xe = ET.SubElement(xe, c)
        if cmd == GET:
            xe.text = 'GetParam'
        elif cmd == PUT:
            if isinstance(data, dict):
                for (k,v) in data.items():
                    ET.SubElement(xe,k).text = str(v)
            else:
                xe.text = str(data)

        body = ET.tostring(xml,encoding='utf-8')
        d = self.queue.add(cmd=cmd, chain=chain, body=body)
        self.send_next()
        return d


    def send_next(self):
        #if self.state not in (''):
        #    return

        if self.queue.get_next() is not None:
            reactor.connectTCP(self.host, self.port, self.factory)
            self.queue.set_timeout(self.timeout, self.timedout)


    def timedout(self):
        # The timeout response is to fail the request and proceed with the next command
        log.msg("Communication timed out.", system=self.system)
        self.setstate('inactive')
        self.queue.errback(TimeoutException())
        self.send_next()



class Yamaha(Endpoint):
    system = 'AVR'
    name = 'YAMAHA'

    # --- Interfaces
    def configure(self):
        self.events = [
            'avr/starting',      # Created avr object
            'avr/stopping',      # close() have been called
            'avr/error',         # Connection failed

            'avr/volume',        # Volume event
            'avr/input',         # Input change event
            'avr/power',         # Change in power
        ]

        self.commands = {
            'avr/state'     : lambda a : self.protocol.state,

            #'avr/raw'     : lambda a : self.protocol.command(*a.args),

            'avr/ison'      : lambda a : self.c(GET, POWER).addCallback(ison),
            'avr/off'       : lambda a : self.c(PUT, POWER, 'Standby'),
            'avr/on'        : lambda a : self.c(PUT, POWER, 'On'),

            'avr/volume'    : lambda a : self.c(GET, VOLUME).addCallback(parse_dB),
            'avr/setvolume' : lambda a : self.c(PUT, VOLUME, dB(a.args[0])),
            'avr/input'     : lambda a : self.c(GET, INPUT).addCallback(t),
            'avr/setinput'  : lambda a : self.c(PUT, INPUT, a.args[0]),
        }


    # --- Initialization
    def __init__(self, host):
        self.host = host
        self.protocol = YamahaProtocol(self,self.host,80)
        self.ssdp = YamahaSSDP(self,self.host,'239.255.255.250')

    def setup(self):
        self.event('avr/starting')
        reactor.listenMulticast(1900, self.ssdp, listenMultiple=True)

    def close(self):
        self.event('avr/stopping')
        self.protocol.disconnect()
        self.ssdp.disconnect()


    # --- Convenience
    def c(self,*args,**kw):
        return self.protocol.command(*args,**kw)


    # --- Callbacks
    def notification(self,notifications):
        if 'Volume' in notifications:
            self.get_command('avr/volume')(None).addCallback(self.event_as_arg,'avr/volume')
        if 'Input' in notifications:
            self.get_command('avr/input')(None).addCallback(self.event_as_arg,'avr/input')
        if 'Power' in notifications:
            self.get_command('avr/ison')(None).addCallback(self.event_as_arg,'avr/ison')


    # --- Commands

# -*-python-*-
import os,sys
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


class YamahaSSDP(DatagramProtocol):
    noisy = False

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

        #log.msg("Datagram %s received from %s" % (repr(datagram), repr(address)), system='AVR')

        # Skip the header (which is HTTP like), and extract the body
        header=True
        body=''
        for line in datagram.split('\r\n'):
            if header:
                if len(line) == 0:
                    header=False
            else:
                body += line

        # Ignore empty bodies
        if len(body)==0:
            #log.msg("Ignoring empty notifications", system='AVR')
            return

        #log.msg("Received '%s' from %s" % (body, repr(address)), system='AVR')

        # Convert to XML
        try:
            root = ET.fromstring(body)

            if root.tag != 'YAMAHA_AV':
                raise SSDPException("'YAMAHA_AV' is not root")
            mz = root.find('Main_Zone')
            if not mz:
                raise SSDPException("'Main_Zone' is missing")

            notifications = [ prop.text for prop in mz.iter('Property') ]
            log.msg("AVR notification: %s" %(notifications,), system='AVR')
            self.parent.notification(notifications)

        except ET.ParseError as e:
            log.msg("Malformed XML, %s. XML='%s'" %(e.message,body), system='AVR')
            return
        except SSDPException as e:
            log.msg("Malformed XML, %s. XML='%s'" %(e.message,body), system='AVR')
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


    def setstate(self,state,*args):
        (old, self.state) = (self.state, state)
        if state != old:
            log.msg("STATE change: '%s' --> '%s'" %(old,state), system=self.system)


    def connectionMade(self):
        self.setstate('connected')
        body = self.queue.active['body']
        myip = self.transport.getHost().host
        data = 'POST /YamahaRemoteControl/ctrl HTTP/1.1\r\nHost: %s\r\nContent-Type: text/html; charset="utf-8"\r\nContent-Length: %s\r\n\r\n%s' %(myip,len(body),body)
        log.msg("     <<<  (%s)'%s'" %(len(data),data), system=self.system)
        self.data = ''
        self.transport.write(data)


    def connectionLost(self, reason):
        self.setstate('closed', reason.getErrorMessage())
        self.send_next()


    def disconnect(self):
        if self.state in ('connected','active'):
            self.transport.loseConnection()


    def dataReceived(self, data):
        self.setstate('active')
        self.data += data
        log.msg("     >>>  (%s)'%s'" %(len(data),data), system=self.system)
        # Process data
        #self.disconnect()
        #self.queue.callback(elements)


    def command(self):
        body = '<?xml version="1.0" encoding="utf-8"?><YAMAHA_AV cmd="GET"><Main_Zone><Volume><Lvl>GetParam</Lvl></Volume></Main_Zone></YAMAHA_AV>'
        body = '<?xml version="1.0" encoding="utf-8"?><YAMAHA_AV cmd="GET"><System><Speaker_Preout><Pattern_2><PEQ><Manual_Data><Front_L>GetParam</Front_L></Manual_Data></PEQ></Pattern_2></Speaker_Preout></System></YAMAHA_AV>'
        d = self.queue.add(body=body)
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

    # --- Interfaces
    def get_events(self):
        return [
            'avr/starting',      # Created avr object
            'avr/stopping',      # close() have been called
            #'avr/connected',     # Connection with Avr has been made
            #'avr/disconnected',  # Lost connection with Avr
            'avr/error',         # Connection failed
        ]

    def get_actions(self):
        return {
            'avr/test'     : lambda a : self.command(),
            #'avr/state'   : lambda a : self.protocol.state,

            #'avr/raw'     : lambda a : self.protocol.command(*a.args),
            #'avr/ison'    : lambda a : self.protocol.command('QPW'),
            #'avr/play'    : lambda a : self.protocol.command('PLA'),
            #'avr/pause'   : lambda a : self.protocol.command('PAU'),
            #'avr/stop'    : lambda a : self.protocol.command('STP'),
            #'avr/on'      : lambda a : self.protocol.command('PON'),
            #'avr/off'     : lambda a : self.protocol.command('POF'),
            #'avr/verbose' : lambda a : self.protocol.command('SVM','2'),
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


    # --- Callbacks
    def notification(self,notifications):
        pass


    # --- Commands
    def command(self):
        body = StringProducer('<?xml version="1.0" encoding="utf-8"?><YAMAHA_AV cmd="GET"><Main_Zone><Volume><Lvl>GetParam</Lvl></Volume></Main_Zone></YAMAHA_AV>')

        agent = Agent(reactor)
        d = agent.request(
            'POST',
            'http://avr/YamahaRemoteControl/ctrl',
            Headers( {
                'Content-Type' : ['text/xml; charset="utf-8"'],
            } ),
            body)
        d.addCallback(self.response)
        d.addErrback(self.error)


    def response(self,req):
        print req
    def error(self,err):
        print err
        raise err


    #def ison(self):
    #    def _ison(result):
    #        if result=='ON':
    #            return 1
    #        else:
    #            return 0
    #    d = self.protocol.command('QPW')
    #    d.addCallback(_ison)
    #    return d

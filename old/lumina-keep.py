# -*-python-*-
import os,sys
from lumina import lumina


from datetime import datetime
import html

from twisted.web.resource import Resource,NoResource
from twisted.web.server import Site
from twisted.internet import reactor
from twisted.internet.protocol import ConnectedDatagramProtocol



class WebBase(Resource):

    def html_init(self,request):
        self.html = html.Document()

        # Header data
        self.html.title = 'Lumina Automation'
        self.html.style = '''
body {
    font-family: sans-serif;
    display: block;
}
'''

        # Header
        #self.html.header += (
        #    html.h1( 'Lumina Automation' ), )

        # Footer
        #self.html.footer += (
        #    html.hr(), 'Bottom' )

        # NAV
        self.html.nav += (
            html.ul(
                     html.li( html.a("Hjem", href="/" ) ),
                     html.li( html.a("Lys", href="/") ),
                     html.li( html.a("AVR", href="/") ),
                 ) )


    def html_render(self):
        return self.html.render()


class PageRoot(WebBase):
    isLeaf = True

    def render_GET(self, request):
        self.html_init(request)
        return self.html_render()


class WebRoot(WebBase):

    #def __init__(self):
    #    pass

    def getChild(self, name, request):
        pages = { '' : PageRoot
              }
        #print "NAME: (%s) '%s' " %(len(name), name)
        if name not in pages:
            print "Unknown resource: %s" %(name)
            return resource.NoResource()
        elif issubclass(pages[name], WebBase):
             return pages[name]()
        else:
             return pages[name]


print os.getpid()

webfactory = Site(WebRoot())
reactor.listenTCP(8080, webfactory)


from twisted.internet.protocol import ClientFactory
from twisted.internet.protocol import Protocol


class TelldusProtocol(Protocol):
     def dataReceived(self, data):
        print "'%s'" %(data)

class Telldus(ClientFactory):
    protocol = TelldusProtocol

    def clientConnectionFailed(self, connector, reason):
        print connector, reason

telldusfactory = Telldus()
reactor.connectUNIX('/tmp/foobar', telldusfactory)

#point = UNIXClientEndpoint(reactor, '/tmp/foobar')
#proto = MyProto()
#d = connectProtocol(point, proto)
#d.addErrback(printError)

#StandardIO(StdinProtocol(proto))



from twisted.internet.endpoints import connectProtocol,UNIXClientEndpoint
from twisted.internet.stdio import StandardIO
from twisted.internet.protocol import Protocol
from twisted.protocols.basic import LineReceiver

class MyProto(Protocol):
    def dataReceived(self, data):
        print "'%s'" %(data)

def printError(failure):
    print str(failure)

class StdinProtocol(LineReceiver):
    from os import linesep as delimiter

    def __init__(self, client):
        self._client = client

    def connectionMade(self):
        self.transport.write('>>> ')

    def lineReceived(self, line):
        print 'writing line: %s' % line
        self._client.transport.write(line + os.linesep)


from twisted.internet.serialport import SerialPort
from twisted.protocols.basic import LineReceiver

class LineProto(LineReceiver):
    delimiter = 'x'

    def lineReceived(self, data):
        print "'%s'" %(data)

s = SerialPort(LineProto(), '/dev/ttyUSB0', reactor, baudrate=115200)


reactor.run()

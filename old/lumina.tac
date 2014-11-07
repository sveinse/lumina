# -*-python-*-
from datetime import datetime
import html
#from HTML import *


#from twisted.application import service, internet
#from twisted.web import server, static
#from twisted.internet import endpoints, protocol

from twisted.web.resource import Resource,NoResource
from twisted.web.server import Site
from twisted.application.service import Application,MultiService
from twisted.application.internet import TCPServer

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
            return NoResource()
        elif issubclass(pages[name], WebBase):
             return pages[name]()
        else:
             return pages[name]


class Telldus(protocol.ConnectedDatagramProtocol):
    pass




services = MultiService()

webfactory = Site(WebRoot())
webservice = TCPServer(8080, webfactory)
webservice.setServiceParent(services)

telldusfactory = Telldus()
telldusservice = internet.UNIXDatagramClient('/tmp/foobar', telldusfactory)
telldusservice.setServiceParent(services)

application = Application("Lumina controller")
services.setServiceParent(application)

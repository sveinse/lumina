from datetime import datetime
import html
#from HTML import *


from twisted.application import service, internet
from twisted.web import server, resource, static
from twisted.internet import reactor


class WebBase(resource.Resource):

    def html_init(self,request):
        self.html = html.Document()

        # Header data
        self.html.title = 'Lumina Automation'
        self.html.style = '''
body {
    font-family: sans-serif;
    display: block;
}

/*nav {
    display: block;
    margin-bottom: 10px;
}
nav ul {
    list-style: none;
    font-size: 18px;
}
nav ul li {
    display: inline;
}
nav ul li a {
    display: block;
    float: left;
    padding: 3px 6px;
    color: #575c7d;
    text-decoration: none;
    font-weight: bold;
}
nav ul li a:hover {
    background: #deff90;
    color: #485e0f;
    -webkit-border-radius: 3px;
    -moz-border-radius: 3px;
    border-radius: 3px;
    padding: 3px 6px;
    margin: 0;
    text-decoration: none;
}*/


/*.nav {
    height: 32px;
    border: 1px;
}
.nav-item {
    background-color: #999999;
    display: inline;
    text-align: center;
    width: 20em;
}*/
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


class LuminaServer():

    def __init__(self):
        self.urllog = 'lumina.log'
        self.port = 8080

    def log(self,*args,**kwargs):
        t = "%s:  " %(datetime.now().ctime())
        t += ' '.join(args)
        t += '\n'
        #if self.logfile:
        #    self.logfile.write(t)
        #    self.logfile.flush()
        #else:
        #    self.logdata.append(t)
        #if 'prnt' in kwargs and kwargs['prnt'] is True:
        #    print t,
        print t,


    def main(self):
        factory = server.Site(WebRoot(), self.urllog)
        reactor.listenTCP(self.port, factory)
        self.log("Starting server on port %s" %(self.port))
        reactor.run()
        self.log("Server stopped")


application = service.Application("Lumina web server")
webfactory = server.Site(WebRoot())
webservice = internet.TCPServer(8080, webfactory)
webservice.setServiceParent(application)

#reactor.listenTCP(8080, webfactory)
#reactor.run()

# -*-python-*-
from __future__ import absolute_import

import os
import json

from twisted.web.resource import Resource, NoResource, ErrorPage
from twisted.web.server import Site, NOT_DONE_YET
import twisted.web.http as http
from twisted.internet import reactor
from twisted.web.static import File
from twisted.web.util import Redirect

#from lumina.event import Event
from lumina.plugin import Plugin
from lumina.state import ColorState
from lumina.log import Logger
from lumina.exceptions import *
#from lumina import html


#class WebException(LuminaException):
#    pass

class LuminaResource(Resource):
    isLeaf = True
    noisy = False

    def __init__(self,main,log):
        self.log = log
        self.main = main



''' FIXME: Need refactor
class PageCtrl(Resource):
    isLeaf = True
    noisy = False
    system = 'WEB'

    def __init__(self,path,controller):
        self.path = '/' + path
        self.controller = controller

    def reply_ok(self, result, request, command):
        #log.msg("RESPONSE: ",command)
        request.responseHeaders.addRawHeader(b'Content-Type', b'application/json')
        request.write(command.dump_json())
        request.finish()

    def reply_error(self, failure, request, command):
        #log.msg("ERROR: ",command)
        reason = failure.value
        request.responseHeaders.addRawHeader(b'Content-Type', b'application/json')
        request.setResponseCode(http.BAD_REQUEST)
        request.write(command.dump_json())
        request.finish()

    def render_POST(self, request):
        #log.msg('HEADERS:',request.requestHeaders)

        # Extract the name from the URI, and do some sanity checks
        if not request.path.startswith(self.path):
            raise WebException("Internal error: Request '%s' does not start with '%s'" %(
                request.path,self.path))
        name = request.path[len(self.path):]
        if not name.startswith('/'):
            return ErrorPage(http.BAD_REQUEST,'Error','Missing request').render(request)
        name = name[1:]
        if not len(name):
            return ErrorPage(http.BAD_REQUEST,'Error','Too short request').render(request)

        content = request.content.read()
        #log.msg("CONTENT: %s '%s'" %(len(content),content,))

        command = Event(name).load_json_args(content)
        command.system = self.system

        # Get the command function and run it
        try:
            cmdlist = self.controller.get_commandfnlist(command)
            defer = self.controller.run_commandlist(command, cmdlist)
            defer.addCallback(self.reply_ok,request,command)
            defer.addErrback(self.reply_error,request,command)
            return NOT_DONE_YET
        except CommandException as e:
            log.err(system=self.system)
            return ErrorPage(http.BAD_REQUEST,'Error in %s' %(command.name,),e.message).render(request)
'''


class RestAdminConfig(LuminaResource):

    def render_GET(self, request):
        request.setHeader(b'Content-Type', b'application/json')
        path = request.postpath[0]

        config = self.main.config.getall()

        if path == '':
            ck = config.keys()
            ck.sort()
        elif path in conf:
            ck = [ path, ]
        else:
            return ErrorPage(http.BAD_REQUEST,'Error','No such config').render(request)

        rlist = [ ]
        for k in ck:
            c = config[k]
            od = {
                'key'     : k,
                'type'    : c.get('type',str).__name__,
                'value'   : c.get('value'),
                'default' : c.get('default'),
                'help'    : c.get('help'),
            }
            rlist.append(od)

        return json.dumps(rlist)



class RestAdminPlugins(LuminaResource):

    def render_GET(self, request):
        request.setHeader(b'Content-Type', b'application/json')
        path = request.postpath[0]

        plugins = self.main.sequence

        if path == '':
            pass
        else:
            return ErrorPage(http.BAD_REQUEST,'Error','No such plugin').render(request)

        rlist = [ ]
        for plugin in plugins:
            p = self.main.plugins[plugin]
            od = {
                'name'      : plugin,
                'module'    : p.module,
                'sequence'  : p.module_sequence,
                'doc'       : p.__doc__,
                'status'    : str(p.status),
                'status_why': p.status.why,
            }
            rlist.append(od)

        return json.dumps(rlist)



class RestAdminNodes(LuminaResource):

    def render_GET(self, request):
        request.setHeader(b'Content-Type', b'application/json')
        path = request.postpath[0]

        server = self.main.get_plugin_by_module('server')
        if not server:
            return ErrorPage(http.BAD_REQUEST,'Error','No server present').render(request)

        nodes = server.nodes

        if path == '':
            pass
        else:
            return ErrorPage(http.BAD_REQUEST,'Error','No such node').render(request)

        rlist = [ ]
        for node in nodes:
            od = {
                'name'      : node.name,
                'host'      : node.host,
                'seqence'   : node.sequence,
                'status'    : node.status,
                'status_why': node.status_why,
                'num_commands': len(node.commands),
                'num_events' : len(node.events),
            }
            rlist.append(od)

        return json.dumps(rlist)



class Web(Plugin):
    ''' Lumina Web server interface.
    '''
    name = 'WEB'

    CONFIG = {
        'port': dict(default=8081, help='Web server port', type=int ),
        'root': dict(default=os.getcwd()+'/www', help='Path for web server files' ),
        'log': dict(default='access-lumina.log', help='Path for web server logs'),
    }

    def setup(self, main):
        self.log = Logger(namespace=self.name)
        self.status = ColorState()

        #self.controller = controller

        self.port = main.config.get('port', name=self.name)
        self.webroot = main.config.get('root', name=self.name)
        self.logpath = main.config.get('log', name=self.name)

        # Setup the rest interfaces
        rest = Resource()
        rest.noisy = False
        rest.putChild('plugins', RestAdminPlugins(main, self.log))
        rest.putChild('config', RestAdminConfig(main, self.log))
        rest.putChild('nodes', RestAdminNodes(main, self.log))

        root = File(self.webroot)
        root.noisy = False
        #root.putChild('', File(os.path.join(self.webroot,'lumina.html')))
        root.putChild('', Redirect('lumina.html'))
        root.putChild('rest', rest)
        #root.putChild('ctrl', PageCtrl('ctrl',self.controller))
        #root.putChild('config', ConfigPage('config',config))

        self.site = Site(root, logPath=self.logpath)
        self.site.noisy = False

        reactor.listenTCP(self.port, self.site)

        self.log.info("Logging access in {p}", p=self.logpath)

        # FIXME: Is there a way to determine up or down?
        self.status.set_GREEN()



PLUGIN = Web
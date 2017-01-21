# -*-python-*-
from __future__ import absolute_import
import os
#import json

from twisted.web.resource import Resource, NoResource, ErrorPage
from twisted.web.server import Site, NOT_DONE_YET
import twisted.web.http as http
from twisted.internet import reactor
from twisted.web.static import File

#from lumina.event import Event
from lumina.plugin import Plugin
from lumina.state import ColorState
from lumina.log import Logger
from lumina.exceptions import *
#from lumina import html


class WebException(LuminaException):
    pass

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

''' FIXME: Need refactor
class ConfigPage(Resource):
    isLeaf = True
    noisy = False
    system = 'WEB'

    def __init__(self,path,config):
        self.path = '/' + path
        self.config = config

    def render_GET(self, request):
        request.setHeader(b'Content-Type', b'application/json')

        # Extract the last part of the path
        path = request.path
        if path.startswith(self.path):
            path = path.replace(self.path,'',1)
        if path.startswith('/'):
            path = path.replace('/','',1)

        # Get a dump of all the settings and modify it to be
        # able to send over JSON
        c = self.config.getall()
        for (k,e) in c.items():
            if 'type' in e:
                e['type'] = e['type'].__name__
            e['key'] = k

        if path == '':
            return json.dumps(c)
        elif path in c:
            return json.dumps(c[path])
        else:
            return ErrorPage(http.BAD_REQUEST,'Error','No such config').render(request)

        return json.dumps(path)
'''


class Web(Plugin):
    name = 'WEB'

    CONFIG = {
        'port': dict(default=8081, help='Web server port', type=int ),
        'root': dict(default=os.getcwd()+'/www', help='Path for web server files' ),
        'log': dict(default='access-lumina.log', help='Path for web server logs'),
    }

    def setup(self, main):
        self.log = Logger(namespace=self.name)

        #self.controller = controller

        self.port = main.config.get('port', name=self.name)
        self.webroot = main.config.get('root', name=self.name)
        self.logpath = main.config.get('log', name=self.name)

        self.status = ColorState()

        root = File(self.webroot)
        root.noisy = False
        root.putChild('', File(os.path.join(self.webroot,'index.html')))
        #root.putChild('ctrl', PageCtrl('ctrl',self.controller))
        #root.putChild('config', ConfigPage('config',config))

        self.site = Site(root, logPath=self.logpath)
        self.site.noisy = False

        reactor.listenTCP(self.port, self.site)

        self.log.info("Logging access in {p}", p=self.logpath)


PLUGIN = Web
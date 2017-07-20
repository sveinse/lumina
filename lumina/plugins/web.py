# -*-python-*-
from __future__ import absolute_import

import os
import json

from twisted.web.resource import Resource, ErrorPage
from twisted.web.server import Site, NOT_DONE_YET
import twisted.web.http as http
from twisted.internet import reactor
from twisted.web.static import File
from twisted.web.util import Redirect
from twisted.internet.defer import maybeDeferred

from lumina.plugin import Plugin
from lumina.event import Event



class LuminaResource(Resource):
    isLeaf = True
    noisy = False

    def __init__(self, main, log):
        Resource.__init__(self)
        self.log = log
        self.main = main
        self.main_server = main.get_plugin_by_module('server')

        # FIXME: Fail if server is not available



def getPath(request):
    if request.postpath:
        return '/'.join(request.postpath)
    else:
        return ''



class RestCommand(LuminaResource):

    def render_POST(self, request):
        request.setHeader(b'Content-Type', b'application/json')
        path = getPath(request)

        server = self.main_server

        #self.log.debug('PATH: {p}', h=path)
        if not path:
            return ErrorPage(http.BAD_REQUEST, 'Error', 'Missing command').render(request)

        #self.log.debug('HEADERS: {h}', h=request.requestHeaders)
        content = request.content.read()
        #self.log.debug("CONTENT: {l} '{c}'", l=len(content), c=content)

        command = Event(path).load_json_args(content)

        def reply_ok(result, request, command):
            self.log.info('', cmdin=command)
            request.responseHeaders.addRawHeader(b'Content-Type', b'application/json')
            request.write(command.dump_json())
            request.finish()

        def reply_error(failure, request, command):
            self.log.info('', cmderr=command)
            request.responseHeaders.addRawHeader(b'Content-Type', b'application/json')
            request.setResponseCode(http.BAD_REQUEST)
            request.write(command.dump_json())
            request.finish()

        self.log.info('', cmdout=command)

        # Requires maybeDeferred() as the server.run_command might not return a deferred object
        #defer = server.run_command(command)
        defer = maybeDeferred(server.run_command, command)
        defer.addCallback(reply_ok, request, command)
        defer.addErrback(reply_error, request, command)
        return NOT_DONE_YET



class RestMainInfo(LuminaResource):
    def render_GET(self, request):
        request.setHeader(b'Content-Type', b'application/json')
        main = self.main
        return json.dumps(main.get_info())


class RestServerInfo(LuminaResource):
    def render_GET(self, request):
        request.setHeader(b'Content-Type', b'application/json')
        server = self.main_server
        if not server:
            return json.dumps({})
        return json.dumps(server.get_info())


class Web(Plugin):
    ''' Lumina Web interface.
    '''

    CONFIG = {
        'port': dict(default=8081, help='Web server port', type=int),
        'root': dict(default=os.getcwd()+'/www', help='Path for web server files'),
        'log': dict(default='access-lumina.log', help='Path for web server logs'),
    }

    def setup(self, main):
        Plugin.setup(self, main)

        self.port = main.config.get('port', name=self.name)
        self.webroot = main.config.get('root', name=self.name)
        self.logpath = main.config.get('log', name=self.name)

        # Creste the root object
        root = File(self.webroot)
        root.noisy = False
        root.putChild('', Redirect('lumina.html'))

        # List of resources that we want added
        resources = {'rest/command': RestCommand(main, self.log),
                     'rest/main/info': RestMainInfo(main, self.log),
                     'rest/server/info': RestServerInfo(main, self.log),
                    }

        # Traverse all resources and add them to the tree. Add empty
        # resources for the path elements between our resources and the root.
        for (path, resource) in resources.items():
            elements = path.split('/')

            # Traverse the path and either append to an existing resource
            # or add a new one.
            base = root
            for element in elements[:-1]:
                res = base.getStaticEntity(element)
                if res is None:
                    res = Resource()
                    res.noisy = False
                base.putChild(element, res)
                base = res      # pylint: disable=redefined-variable-type

            # Add our resource to the tree
            base.putChild(elements[-1], resource)

        # Create the site
        self.site = Site(root, logPath=self.logpath)
        self.site.noisy = False

        reactor.listenTCP(self.port, self.site)

        self.log.info("Logging access in {p}", p=self.logpath)

        # FIXME: Is there a way to determine up or down?
        self.status.set_GREEN()



PLUGIN = Web

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
from lumina.message import MsgCommand
from lumina import utils
from lumina.exceptions import TimeoutException
from lumina.lumina import master


COMMAND_TIMEOUT = 10


def getPath(request):
    if request.postpath:
        return '/'.join(request.postpath)
    else:
        return ''


class LuminaResource(Resource):
    isLeaf = True
    noisy = False
    command_timeout = COMMAND_TIMEOUT


    def __init__(self, log):
        Resource.__init__(self)
        self.log = log
        self.master_server = master.get_plugin_by_module('server')


    def run_command(self, command):
        self.log.info('', cmdout=command)

        defer = maybeDeferred(self.master_server.run_command, command)

        def cmd_ok(result):
            command.set_success(result)
            self.log.info('', cmdin=command)
            return result

        def cmd_error(failure):
            command.set_fail(failure)
            self.log.info('', cmderr=command)
            return failure

        def cmd_timeout():
            ''' Response if command suffers a timeout '''
            exc = TimeoutException()
            command.set_fail(exc)
            self.log.error('REQUEST TIMED OUT')
            defer.errback(exc)

        # -- Setup a timeout, and add a timeout err handler making sure the
        #    message data failure is properly set
        utils.add_defer_timeout(defer, self.command_timeout, cmd_timeout, command)
        
        defer.addCallback(cmd_ok)
        defer.addErrback(cmd_error)
        return defer


    def web_command(self, request, command):
        ''' Front-end command for running Lumina commands '''

        def reply_ok(result):  # pylint: disable=unused-variable
            request.responseHeaders.addRawHeader(b'Content-Type', b'application/json')
            request.write(command.dump_json())
            request.finish()

        def reply_error(failure):  # pylint: disable=unused-variable
            request.responseHeaders.addRawHeader(b'Content-Type', b'application/json')
            request.setResponseCode(http.BAD_REQUEST)
            request.write(command.dump_json())
            request.finish()

        # Do not add a timeout handler here. The server.run_command will
        # time out and call our errback function
        self.run_command(command).addCallback(reply_ok).addErrback(reply_error)
        return NOT_DONE_YET



class RestCommand(LuminaResource):
    def render_POST(self, request):
        request.setHeader(b'Content-Type', b'application/json')
        request.setHeader(b'Cache-Control', b'no-cache, no-store, must-revalidate')
        path = getPath(request)

        #self.log.debug('PATH: {p}', h=path)
        if not path:
            return ErrorPage(http.BAD_REQUEST, 'Error', 'Missing command').render(request)

        #self.log.debug('HEADERS: {h}', h=request.requestHeaders)
        content = request.content.read()
        #self.log.debug("CONTENT: {l} '{c}'", l=len(content), c=content)
        command = MsgCommand(path).load_json_args(content)
        return self.web_command(request, command)



class RestInfo(LuminaResource):
    def render_GET(self, request):
        request.setHeader(b'Content-Type', b'application/json')
        request.setHeader(b'Cache-Control', b'no-cache, no-store, must-revalidate')
        path = getPath(request)

        if path == '':
            path = '_info'
        if path in ('_info', '_server'):
            command = MsgCommand(path)
        else:
            # All others refer to remote nodes
            command=MsgCommand(path + '/_info')

        return self.web_command(request, command)



class Web(Plugin):
    ''' Lumina Web interface.
    '''

    CONFIG = {
        'port': dict(default=8081, help='Web server port', type=int),
        'root': dict(default=os.getcwd()+'/www', help='Path for web server files'),
        'log': dict(default='access-lumina.log', help='Path for web server logs'),
    }

    DEPENDS = ('server', 'responder')

    def setup(self):

        self.port = master.config.get('port', name=self.name)
        self.webroot = master.config.get('root', name=self.name)
        self.logpath = master.config.get('log', name=self.name)

        # Creste the root object
        root = File(self.webroot)
        root.noisy = False
        root.putChild('', Redirect('lumina.html'))

        # List of resources that we want added
        resources = {'rest/command': RestCommand(self.log),
                     'rest/info': RestInfo(self.log),
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

        # Ready
        self.status.set_GREEN()



PLUGIN = Web

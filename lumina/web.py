# -*-python-*-
import os,sys
import html

from twisted.web.resource import Resource,NoResource,ErrorPage
from twisted.web.server import Site,NOT_DONE_YET
import twisted.web.http as http
from twisted.internet import reactor
from twisted.web.static import File
from twisted.python import log
from twisted.internet.defer import Deferred,maybeDeferred
import json

from event import Event
from exceptions import *

class WebException(LuminaException):
    pass


class PageCtrl(Resource):
    isLeaf = True
    noisy = False
    system = 'WEB'

    def __init__(self,path,controller):
        self.path = '/' + path
        self.controller = controller

    def reply_ok(self, result, request):
        request.responseHeaders.addRawHeader(b'Content-Type', b'application/json')
        if isinstance(result,Event):
            response = result.dump_json()
        else:
            response=''
            for r in response:
                response += r.dump_json()
        #log.msg('RESPONSE:',request.responseHeaders)
        #log.msg("RESPONSE: '%s'" %(response,))
        request.write(response)
        request.finish()

    def reply_error(self, failure, request):
        failtype = failure.trap(CommandException)
        reason = failure.value

        request.write(json.dumps(failure))
        request.finish()

    def render_POST(self, request):
        #log.msg('HEADERS:',request.requestHeaders)

        # Extract the command from the URI, and do some sanity checks
        if not request.path.startswith(self.path):
            raise WebException("Internal error: Request '%s' does not start with '%s'" %(
                request.path,self.path))
        command = request.path[len(self.path):]
        if not command.startswith('/'):
            return ErrorPage(http.BAD_REQUEST,'Error','Missing request').render(request)
        command = command[1:]
        if not len(command):
            return ErrorPage(http.BAD_REQUEST,'Error','Too short request').render(request)

        content = request.content.read()
        #log.msg("CONTENT: '%s'" %(content,))

        event = Event(command) #.jparse(request.content.read())

        # Get the command function and run it
        try:
            result = self.controller.run_command(event)
            result.addCallback(self.reply_ok,request)
            result.addErrback(self.reply_error,request)
        except CommandError as e:
            return ErrorPage(http.BAD_REQUEST,'Error in %s' %(event.name,),e.message).render(request)
        return NOT_DONE_YET



class Web(object):

    def __init__(self,port,webroot):
        self.port = port
        self.webroot = webroot

    def setup(self, controller):
        self.controller = controller

        root = File(self.webroot)
        root.noisy = False
        root.putChild('', File(os.path.join(self.webroot,'index.html')))
        root.putChild('ctrl', PageCtrl('ctrl',self.controller))

        self.site = Site(root)
        reactor.listenTCP(self.port, self.site)

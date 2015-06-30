import os,sys

from twisted.web.resource import Resource,NoResource
from twisted.web.server import Site
from twisted.internet import reactor
from twisted.web.static import File
from twisted.python import log
from twisted.web.server import NOT_DONE_YET


class EventPage(Resource):
    isLeaf = True

    #def getChild(self, name, request):
    #    log.msg("getChild(%s,%s)" %(name,request))
    #    return NoResource()

    def render_GET(self, request):
        log.msg("render_GET: %s" %(request))
        return ''


class ActionPage(Resource):
    isLeaf = True

    def __init__(self,controller):
        self.controller = controller
        self.requests = []

    def render_GET(self, request):
        self.requests.appned(request)
        return NOT_DONE_YET

    def send(self, msg):
        for p in self.requests:
            p.write(msg)


class PageRoot(Resource):
    isLeaf = True

    def __init__(self,path):
        self.path = path

    def render_GET(self, request):
        #log.msg("render_GET: %s" %(request))
        params = {
            'foo': 'bar'
        }
        with open(self.path, 'r') as f:
            data = f.read().format(**params)
        return data


class Controller(object):

    def __init__(self,port):
        self.port = port

    def setup(self):
        root = File('www')
        root.putChild('', PageRoot('www/index.html'))
        root.putChild('event', EventPage())
        self.action = ActionPage(self)
        root.putChild('action', self.action)

        self.site = Site(root)
        reactor.listenTCP(self.port, self.site)

    def send(self, msg):
        self.action(msg)

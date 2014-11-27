# -*-python-*-
import os,sys
import html

from twisted.web.resource import Resource,NoResource
from twisted.web.server import Site
from twisted.internet import reactor
from twisted.web.static import File
from twisted.python import log


class Rest(Resource):
    isLeaf = True

    #def getChild(self, name, request):
    #    log.msg("getChild(%s,%s)" %(name,request))
    #    return NoResource()

    def render_GET(self, request):
        log.msg("render_GET: %s" %(request))
        return ''


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


def setup():
    root = File('www')
    root.putChild('', PageRoot('www/index.html'))
    root.putChild('rest', Rest())

    webfactory = Site(root)
    reactor.listenTCP(8080, webfactory)

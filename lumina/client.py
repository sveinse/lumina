import os,sys


class Client(object):

    def __init__(self,host,port):
        self.host = host
        self.port = port

    def setup(self):
        root = File('www')
        root.putChild('', PageRoot('www/index.html'))
        root.putChild('event', Event())
        self.action = Action(self)
        root.putChild('action', self.action)

        self.site = Site(root)
        reactor.listenTCP(self.port, self.site)

    def send(self, msg):
        self.action(msg)

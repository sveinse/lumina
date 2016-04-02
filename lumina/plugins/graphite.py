# -*- python -*-
from twisted.python import log
from twisted.internet.protocol import Protocol, ClientFactory
#from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
#from twisted.internet.protocol import DatagramProtocol, ClientFactory, Protocol
from twisted.internet import reactor
import pickle
import time
import struct

from ..endpoint import Endpoint
from ..event import Event
from ..callback import Callback


class GraphiteProtocol(Protocol):
    noisy = False
    system = 'GRAPHITE'

    def __init__(self,msg):
        self.msg = msg

    def connectionMade(self):
        self.transport.write(self.msg.encode('ascii'))
        self.transport.loseConnection()


class GraphiteFactory(ClientFactory):
    noisy = False
    system = 'GRAPHITE'

    def __init__(self, host, port, msg):
        self.host = host
        self.port = port
        self.protocol = GraphiteProtocol(msg)
        reactor.connectTCP(self.host, self.port, self)

    def buildProtocol(self, addr):
        return self.protocol


class Graphite(Endpoint):
    name = 'GRAPHITE'

    CONFIG = {
        'graphite_host': dict(default='localhost', help='Graphite host'),
        'graphite_port': dict(default=2003, help='Graphite port', type=int),
    }

    # --- Interfaces
    def configure(self):
        self.events = [
        ]

        self.commands = {
            'graphite/send' : lambda a : self.send(a),
        }


    # Graphite mappings
    NAMES = {
        'temp/ute'       : 'hus.ute',
        'temp/kjeller'   : 'hus.kjeller',
        'temp/fryseskap' : 'hus.fryseskap',
        'temp/kino/ute'  : 'hus.kino_ute',
        'temp/kino/inne' : 'hus.kino_inne',
    }

    # --- Initialization
    def setup(self, config):
        self.host = config['graphite_host']
        self.port = config['graphite_port']


    def send(self,a):
        t = time.time()
        n = self.NAMES[a.args[0]]

        GraphiteFactory(self.host, self.port, "%s.temp %s %s\n" %(n,a.args[1],t) )
        if len(a.args) > 2:
            GraphiteFactory(self.host, self.port, "%s.humidity %s %s\n" %(n,a.args[2],t) )

        #l = [ ( n+'.temp', (t, a.args[1]) ) ]
        #if len(a.args) > 2:
        #    l += [ ( n+'.humidity', (t, a.args[2]) ) ]
        #payload = pickle.dumps(l, protocol=2)
        #header = struct.pack("!L", len(payload))
        #message = header + payload
        #GraphiteFactory(self.host, self.port, message)


# Main plugin object class
PLUGIN = Graphite

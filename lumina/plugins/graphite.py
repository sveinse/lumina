# -*- python -*-
from twisted.python import log
from twisted.internet.protocol import Protocol, ClientFactory
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
        self.transport.write(self.msg)   #.encode('ascii')) # <-- Needed for text based reporting
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
    system = 'GRAPHITE'

    CONFIG = {
        'graphite_host': dict(default='localhost', help='Graphite host'),
        'graphite_port': dict(default=2004, help='Graphite port', type=int),
    }


    # --- Interfaces
    def configure(self):
        self.events = [
        ]

        self.commands = {
            'graphite/send' : lambda a : self.send(a),
        }


    # --- Initialization
    def setup(self, config):
        self.host = config['graphite_host']
        self.port = config['graphite_port']

        self.cache = { }


    def send(self,a):
        n = a.args[0]
        t = time.time()

        #v = a.args[1:]
        #GraphiteFactory(self.host, self.port, "%s %s %s\n" %(n+'.'+v[0][0],v[0][1],t) )
        #if len(v) > 1:
        #    GraphiteFactory(self.host, self.port, "%s %s %s\n" %(n+'.'+v[1][0],v[1][1],t) )

        val = float(a.args[1][1])
        last = self.cache.get(n,None)
        if last is not None and abs(val-last) > 20:
            log.msg("Ignoring %s temperature of %s (last %s)" %(n,val,last), system=self.system)
            return
        self.cache[n] = val

        l = []
        for v in a.args[1:]:
            l += [ ( n+'.'+v[0], (t, v[1]) ) ]
        payload = pickle.dumps(l, protocol=2)
        header = struct.pack("!L", len(payload))
        message = header + payload
        GraphiteFactory(self.host, self.port, message)


# Main plugin object class
PLUGIN = Graphite

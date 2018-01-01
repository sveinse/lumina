# -*-python-*-
from __future__ import absolute_import

#from twisted.internet import reactor
#from twisted.internet.protocol import Protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet.endpoints import UNIXClientEndpoint
from twisted.internet.defer import Deferred

from lumina.plugin import Plugin
from lumina.utils import connectEndpoint
from lumina.exceptions import CommandRunException #, TimeoutException
from lumina.lumina import master

# Protocol response:
#   BEGIN
#   SEND_ONCE Yamaha_RXV757 KEY_PURE_DIRECT
#   SUCCESS
#   END
#
# Protocol error:
#   BEGIN
#   SEND_ONCE Yamaha_RXV757 KEY_PURE_DIRECTs
#   ERROR
#   DATA
#   1
#   unknown command: "KEY_PURE_DIRECTs"
#   END


class LircProtocol(LineReceiver):
    delimiter = '\n'

    CONFIG = {
        'port': dict(default='/var/run/lirc/lircd', help='LIRC communication port'),
    }

    # FIXME: Add proper timeout handling

    def __init__(self, parent, command, port):
        self.log = parent.log
        self.status = parent.status
        self.command = command
        self.port = port
        self.defer = Deferred()

        connectEndpoint(self, UNIXClientEndpoint, self.port)


    def connectionMade(self):
        self.status.set_YELLOW('Connecting')
        self.log.debug('', dataout=self.command)
        self.transport.write(self.command)


    #def connectionLost(self, reason):
    #    self.log.info("Conneciton lost: {c}", c=reason)
    #    self.status.set_OFF()


    def lineReceived(self, data):
        self.log.debug('', datain=data)
        if data == 'BEGIN':
            pass
        elif data == 'SUCCESS':
            self.status.set_GREEN()
            self.defer.callback(None)
        elif data == 'ERROR':
            self.status.set_RED()
            # FIXME: Extract the error message
            self.defer.errback(CommandRunException())
        elif data == 'END':
            self.transport.loseConnection()



class Lirc(Plugin):
    ''' IR control interface '''

    CONFIG = {
        'port': dict(default='/var/run/lirc/lircd', help='LIRC communication port'),
    }


    # --- Interfaces
    def configure(self):

        self.events = (
        )

        self.commands = {
        }


    # --- Initialization
    def setup(self):

        self.port = master.config.get('port', name=self.name)
        self.status.set_OFF()


    def command(self, op, name, key):
        command = '%s %s %s\n' %(op, name, key)

        lp = LircProtocol(self, command, self.port)
        return lp.defer

        #d = Deferred()
        #connectEndpoint(LircProtocol(self, command, d),
        #                UNIXClientEndpoint, self.port)
        #return d



PLUGIN = Lirc

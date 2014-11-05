from twisted.internet import reactor
from twisted.python import log
from twisted.internet.protocol import ClientFactory
from twisted.internet.protocol import Protocol
from twisted.internet.defer import Deferred
from deferred import MyDeferred


class MyProtocol(Protocol):
    def dataReceived(self, data):
        event = self.parse_data(data)
        self.factory.receivedEvent(cmd, event)


class MyFactory(ClientFactory):
    protocol = MyProtocol

    def __init__(self, deferred):
        self.deferred = deferred

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)

    def receivedEvent(self, event):
        if self.deferred is not None:
            d = self.deferred
            d.callback(event)
            d.reset()

def setup_events():
    d = MyDeferred()
    factory = MyFactory(d)
    reactor.connectUNIX('/tmp/TelldusEvents', factory)
    self.eventfactory = factory
    return d


#
# From the top main part of the application:
#

def handle_error(reason):
    print reason

def handle_event(event):
    # Respond to the event
    pass


def main():

    d = setup_events()
    d.addCallback(handle_event)
    d.addErrback(handle_error)

    reactor.run()

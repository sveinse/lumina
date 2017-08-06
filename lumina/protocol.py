# -*- python -*-
from __future__ import absolute_import

from datetime import datetime

from twisted.protocols.basic import LineReceiver
from twisted.internet.defer import Deferred, maybeDeferred

from lumina.event import Event
from lumina import utils
from lumina.exceptions import (NodeException, NoConnectionException,
                               TimeoutException, UnknownCommandException)
from lumina.state import ColorState

#
# LuminaProtocol
# ==============
#    1. JSON encoded messages, Event() objects:
#       {
#          'name':        # Name of the event/command
#          'args':        # Arg list [optional]
#          'kw':          # Arg dict [optional]
#          'requestid':   # None: No response required
#                         #     : Response is requested
#          'response':    # None: A request/command message
#                         #     : A response message
#          'result':      # Result of the request
#       }
#
#    2. Client connects to server. Either client or server
#       can initiate new messages after connection.
#
#    3. If event.requestid is not None on an incoming request
#        - A response is requested using same requestid
#        - The receiver will call event.defer on the original
#          request with incoming results
#
#    4. Special Node() -> Server() operations
#        * register - Register node (client) capability
#        * status - Report node status to server
#

# FIXME: Add this as a config statement

# Maxiumum processing time by peer when issuing a remote command
REMOTE_TIMEOUT = 10
COMMAND_TIMEOUT = 10


# Exception types that will not result in a local traceback
validNodeExceptions = (
    NodeException,
    NoConnectionException,
    TimeoutException
)


class LuminaProtocol(LineReceiver):
    noisy = False
    delimiter = '\n'
    remote_timeout = REMOTE_TIMEOUT
    command_timeout = COMMAND_TIMEOUT


    def __init__(self, parent):
        self.parent = parent
        self.log = parent.log

        # Setup support for a keepalive timer, but dont create it. This must
        # be done in inheriting classes
        self.keepalive = None

        # Setup status for the link
        self.link = ColorState(log=self.log, state='OFF', why='Not connected', what='LINK')


    def connectionMade(self):
        self.peer = "%s:%s" %(self.transport.getPeer().host, self.transport.getPeer().port)

        self.name = self.peer
        self.link.name = self.name
        self.lastactivity = datetime.utcnow()

        self.requests = {}

        self.link.set_YELLOW('Connecting')


    def connectionLost(self, reason):
        self.link.set_RED('Connection lost')

        # -- Cancel timer
        if self.keepalive and self.keepalive.running:
            self.keepalive.stop()

        # -- Cancel any pending requests
        for (requestid, request) in self.requests.items():
            exc = NoConnectionException()
            request.set_fail(exc)

            # A send() timeout exception will call the errback on that
            # event, so prevent failing on already called deferreds
            if not request.defer.called:
                request.defer.errback(exc)


    def lineReceived(self, data):

        # -- Reset the timer
        if self.keepalive and self.keepalive.running:
            self.keepalive.reset()

        # -- Empty lines are simply ignored
        if not len(data):
            return

        self.log.debug('', rawin=data)

        # -- Parse the incoming message
        try:
            event = Event().load_json(data)
            self.log.debug('', cmdin=event)

        except (SyntaxError, ValueError) as e:
            # Raised if the load_json didn't succeed
            self.log.error("Protocol error on incoming message: {e}", e.message)
            return

        # -- Update the activity timer
        self.lastactivity = datetime.utcnow()

        # -- Link is up
        self.link.set_GREEN('Up')

        # -- Handle 'exit' event
        if event.name == 'exit':
            self.transport.loseConnection()
            return

        # -- Handle reply to a former request
        if event.response is not None:

            # Not much to do if we are not expecting a reply. I.e. the deferred
            # has already fired.
            if event.requestid not in self.requests:
                self.log.error("Dropping unexpeced response. Late reply from a previous timed out request?")
                return

            # Get orginial request and delete it from the queue.
            request = self.requests.pop(event.requestid)
            self.log.debug("       ^^ is a reply to {re}", re=request)

            # Copy received data into request
            request.response = event.response
            request.result = event.result

            # Get the defer handler and remove it from the request to prevent
            # calling it twice
            (defer, request.defer) = (request.defer, None)

            if event.response:

                # Send successful result back
                self.log.info('', cmdok=request)
                defer.callback(request)
            else:

                def cmd_error(failure):
                    # Print the error
                    #self.log.error('{tb}', tb=failure.getTraceback())

                    # Eat the error message
                    return None

                # Add an eat-error message to the end of the chain
                defer.addErrback(cmd_error)

                # Send an error back
                exc = NodeException(*request.result)
                self.log.error('', cmderr=request)
                defer.errback(exc)

        # -- New incoming request
        else:

            # -- Process the request
            defer = maybeDeferred(self.commandReceived, event)

            # -- Setup filling in the event data from the result
            def cmd_ok(result, event):
                event.set_success(result)
                self.log.info('', cmdok=event)
                return result

            def cmd_error(failure, event):
                event.set_fail(failure)

                # Accept the exception if listed in validNodeExceptions.
                for exc in validNodeExceptions:
                    if failure.check(exc):
                        return None

                # Print the error and dump the traceback
                self.log.error('REQUEST FAILED: {tb}', tb=failure.getTraceback())

                # Eat the error message
                return None

            def cmd_timeout(event):
                ''' Response if command suffers a timeout '''
                exc = TimeoutException()
                event.set_fail(exc)
                self.log.error('REQUEST TIMED OUT')
                defer.errback(exc)

            # -- Setup a timeout, and add a timeout err handler making sure the
            #    event data failure is properly set
            utils.add_defer_timeout(defer, self.command_timeout, cmd_timeout, event)

            defer.addCallback(cmd_ok, event)
            defer.addErrback(cmd_error, event)

            # If requestid is set, the caller expects a reply.
            if event.requestid is not None:

                # Send response back to sender when the defer object fires
                defer.addBoth(lambda r, c: self.send(c), event)


    def commandReceived(self, event):
        ''' Process an incoming event or command. This method should return
            a Deferred() if results are not immediately available
        '''
        raise UnknownCommandException(event.name)


    def send(self, event, request_response=True):

        # There are three originators calling this function:
        #
        #   a) Send response to former command (from lineReceived())
        #         request_response = True (by default)
        #         event.requestid = not None
        #   b) Send new command (from request_raw())
        #         request_response = True
        #         event.requestid = None
        #   c) Send new event (from emit_raw())
        #         request_response = False
        #         event.requestid = None

        # -- Generate deferred and setup timeout if this is a new command
        #    to send (case b)
        defer = None
        if event.requestid is None and request_response:

            # -- Generate a deferred object
            event.defer = defer = Deferred()

            def timeout(event):
                ''' Response if command suffers a timeout '''
                self.link.set_YELLOW('Communication timeout')
                self.requests.pop(event.requestid)
                exc = TimeoutException()
                event.set_fail(exc)
                event.defer.errback(exc)

            # -- Setup a timeout, and add a timeout err handler making sure the
            #    event data failure is properly set
            utils.add_defer_timeout(defer, self.remote_timeout, timeout, event)

            # -- Generate new requestid for request, save it in request list
            self.requests[event.gen_requestid()] = event

        # -- Encode and send the command
        self.log.debug('', cmdout=event)
        data = event.dump_json()
        self.log.debug('', rawout=data)
        self.transport.write(data+'\n')

        return defer


    # -- Easy-to-remember wrapper functions for self.send()
    def emit(self, name, *args, **kw):
        return self.emit_raw(Event(name, *args, **kw))

    def emit_raw(self, event):
        return self.send(event, request_response=False)

    def request(self, name, *args, **kw):
        return self.request_raw(Event(name, *args, **kw))

    def request_raw(self, event):
        return self.send(event, request_response=True)

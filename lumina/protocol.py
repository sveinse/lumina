# -*- python -*-
from __future__ import absolute_import

from datetime import datetime

from twisted.protocols.basic import LineReceiver
from twisted.internet.defer import Deferred, maybeDeferred

from lumina.event import Event
from lumina import utils
from lumina.exceptions import (NodeException, NoConnectionException,
                               TimeoutException, UnknownCommandException)

#
# LuminaProtocol
# ==============
#    1. Either client and server can initiate message
#        - Sends Event() objects
#        - json encoded message
#
#    2. event.success in message determines
#        - None: A request.
#        - not None: A response.
#
#    3. If event.seq is set (not None) on an incoming request
#        - A response is requested
#        - Will call event.defer with incoming results
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


    def connectionMade(self):
        self.peer = "%s:%s" %(self.transport.getPeer().host, self.transport.getPeer().port)

        self.name = self.peer
        self.lastactivity = datetime.utcnow()

        self.requests = {}


    def connectionLost(self, reason):
        # -- Cancel timer
        if self.keepalive and self.keepalive.running:
            self.keepalive.stop()

        # -- Cancel any pending requests
        for (seq, request) in self.requests.items():
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
            # Load string mode with shell-like parsing in interactive mode
            #event = Event().load_str(data, shell=True)

            self.log.debug('', cmdin=event)

        except (SyntaxError, ValueError) as e:
            # Raised if the load_json didn't succeed
            self.log.error("Protocol error on incoming message: {e}", e.message)
            return

        # -- Update the activity timer
        self.lastactivity = datetime.utcnow()

        # -- Handle 'exit' event
        if event.name == 'exit':
            self.transport.loseConnection()
            return

        # -- Handle reply to a former request
        if event.success is not None:

            # Get orginial request and delete it from the queue.
            request = self.requests.pop(event.seq)
            self.log.debug("       ^^ is a reply to {re}", re=request)

            # Copy received data into request
            request.success = event.success
            request.result = event.result

            # Get the defer handler and remove it from the request to prevent
            # calling it twice
            (defer, request.defer) = (request.defer, None)

            if event.success:

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

            # If seq is set, the caller expects a reply.
            if event.seq is not None:

                # Send response back to sender when the defer object fires
                defer.addBoth(lambda r, c: self.send(c), event)


    def commandReceived(self, event):
        ''' Process an incoming event or command. This method should return
            a Deferred() if results are not immediately available
        '''
        raise UnknownCommandException(event.name)


    def send(self, event, request_response=True):

        # There are three ways calling this function:
        #   a) Send response to former command (from lineReceived())
        #         request_response = True (by default)
        #         event.seq = <value>
        #   b) Send new command (from request_raw())
        #         request_response = True
        #         event.seq = None
        #   c) Send new event (from emit_raw())
        #         request_response = False
        #         event.seq = None

        # -- Generate deferred and setup timeout if this is a new command
        #    to send (case b)
        defer = None
        if event.seq is None and request_response:

            # -- Generate a deferred object
            event.defer = defer = Deferred()

            def timeout(event):
                ''' Response if command suffers a timeout '''
                exc = TimeoutException()
                event.set_fail(exc)
                event.defer.errback(exc)

            # -- Setup a timeout, and add a timeout err handler making sure the
            #    event data failure is properly set
            utils.add_defer_timeout(defer, self.remote_timeout, timeout, event)

            # -- Generate new seq for request, save it in request list
            self.requests[event.gen_seq()] = event

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

# -*- python -*-
from __future__ import absolute_import

from datetime import datetime

from twisted.protocols.basic import LineReceiver
from twisted.internet.defer import Deferred, maybeDeferred

from lumina.message import Message
from lumina import utils
from lumina.exceptions import (NodeException, NoConnectionException,
                               TimeoutException, UnknownCommandException)
from lumina.state import ColorState

#
# LuminaProtocol
# ==============
#    1. JSON encoded messages, Message() objects:
#       {
#          'name':        # Name of the message (event/command)
#          'args':        # Arg list [optional]
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
#    3. If message.requestid is not None on an incoming request
#        - A response is requested using same requestid
#        - The receiver will call message.defer on the original
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
            # request, so prevent failing on already called deferreds
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
            message = Message().load_json(data)
            self.log.debug('', cmdin=message)

        except (SyntaxError, ValueError) as e:
            # Raised if the load_json didn't succeed
            self.log.error("Protocol error on incoming message: {e}", e.message)
            return

        # -- Update the activity timer
        self.lastactivity = datetime.utcnow()

        # -- Link is up
        self.link.set_GREEN('Up')

        # -- Handle 'exit' message
        if message.name == '_exit':
            self.transport.loseConnection()
            return

        # -- Handle reply to a former request
        if message.response is not None:

            # Not much to do if we are not expecting a reply. I.e. the deferred
            # has already fired.
            if message.requestid not in self.requests:
                self.log.error("Dropping unexpeced response. Late reply from a previous timed out request?")
                return

            # Get orginial request and delete it from the queue.
            request = self.requests.pop(message.requestid)
            #self.log.debug("       ^^ is a reply to {re}", re=request)

            # Link the request with the response by copying the
            # received data into the request
            request.response = message.response
            request.result = message.result

            # Get the defer handler and remove it from the request to prevent
            # calling it twice
            (defer, request.defer) = (request.defer, None)

            # Remote request successful
            if message.response:

                # Send successful result back
                self.log.info('', cmdok=request)
                defer.callback(request)

            # Remote request failed
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
            defer = maybeDeferred(self.commandReceived, message)

            # -- Setup filling in the message data from the result
            def cmd_ok(result, message):
                message.set_success(result)
                self.log.info('', cmdok=message)
                return result

            def cmd_error(failure, message):
                message.set_fail(failure)

                # Accept the exception if listed in validNodeExceptions.
                for exc in validNodeExceptions:
                    if failure.check(exc):
                        return None

                # Print the error and dump the traceback
                self.log.error('REQUEST FAILED: {tb}', tb=failure.getTraceback())

                # Eat the error message
                return None

            def cmd_timeout(message):
                ''' Response if command suffers a timeout '''
                exc = TimeoutException()
                message.set_fail(exc)
                self.log.error('REQUEST TIMED OUT')
                defer.errback(exc)

            # -- Setup a timeout, and add a timeout err handler making sure the
            #    message data failure is properly set
            utils.add_defer_timeout(defer, self.command_timeout, cmd_timeout, message)

            defer.addCallback(cmd_ok, message)
            defer.addErrback(cmd_error, message)

            # If requestid is set, the caller expects a reply.
            if message.requestid is not None:

                # Send response back to sender when the defer object fires
                defer.addBoth(lambda r, c: self.send(c), message)


    def commandReceived(self, message):
        ''' Process an incoming command. This method should return
            a Deferred() if results are not immediately available
        '''
        raise UnknownCommandException(message.name)


    def send(self, message, request_response=True):

        # There are three originators calling this function:
        #
        #   a) Send response to former command (from lineReceived())
        #         request_response = True (by default)
        #         message.requestid = not None
        #   b) Send new command (from request_raw())
        #         request_response = True
        #         message.requestid = None
        #   c) Send new event (from emit_raw())
        #         request_response = False
        #         message.requestid = None

        # -- Generate deferred and setup timeout if this is a new command
        #    to send (case b)
        defer = None
        if message.requestid is None and request_response:

            # -- Generate a deferred object
            message.defer = defer = Deferred()

            def timeout(message):
                ''' Failure if remote command suffers a timeout '''
                self.link.set_YELLOW('Communication timeout')
                self.requests.pop(message.requestid)
                exc = TimeoutException()
                message.set_fail(exc)
                message.defer.errback(exc)

            # -- Setup a timeout, and add a timeout err handler making sure the
            #    message data failure is properly set
            utils.add_defer_timeout(defer, self.remote_timeout, timeout, message)

            # -- Generate new requestid for request, save it in request list
            self.requests[message.gen_requestid()] = message

        # -- Encode and send the command
        self.log.debug('', cmdout=message)
        data = message.dump_json()
        self.log.debug('', rawout=data)
        self.transport.write(data+'\n')

        return defer


    # -- Easy-to-remember wrapper functions for self.send()
    def emit(self, name, *args):
        return self.emit_raw(Message(name, *args))

    # FIXME: Should set proper type
    def emit_raw(self, message):
        return self.send(message, request_response=False)

    def request(self, name, *args):
        return self.request_raw(Message(name, *args))

    def request_raw(self, message):
        return self.send(message, request_response=True)

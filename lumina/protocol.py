# -*- python -*-
""" Lumina communication protocol """
from __future__ import absolute_import, division, print_function

from datetime import datetime

from twisted.protocols.basic import LineReceiver
from twisted.internet.defer import Deferred, maybeDeferred

from lumina.message import Message
from lumina.utils import add_defer_timeout
from lumina.exceptions import (NodeException, NoConnectionException,
                               TimeoutException, UnknownMessageException)
from lumina.state import ColorState

#
# LuminaProtocol
# ==============
#    1. JSON encoded messages, Message() inherited objects:
#       {
#          'type':        # Type object (see message.py)
#          'name':        # Name of the message
#       // Optional args:
#          'args':        # Args list
#          'requestid':   # None: No response required
#                         #     : Response is requested
#          'response':    # None: A request/command message
#                         #     : A response message
#          'result':      # Result of the request (present if response is
#                         # present
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
VALID_NODE_EXCEPTIONS = (
    NodeException,
    NoConnectionException,
    TimeoutException
)


class LuminaProtocol(LineReceiver):
    ''' Lumina communication protocol '''
    noisy = False
    delimiter = '\n'
    remote_timeout = REMOTE_TIMEOUT
    command_timeout = COMMAND_TIMEOUT


    def __init__(self, parent):
        self.parent = parent
        self.log = parent.log
        self.master = parent.master

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


    def connectionLost(self, reason):  # pylint: disable=W0222
        self.link.set_RED('Connection lost')

        # -- Cancel timer
        if self.keepalive and self.keepalive.running:
            self.keepalive.stop()

        # -- Cancel any pending requests
        for (requestid, request) in self.requests.items():  # pylint: disable=unused-variable
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

        self.log.debug('{_rawin}', rawin=data)

        # -- Parse the incoming message
        try:
            message = Message.create_from_json(data)
            self.log.debug('{_cmdin}', cmdin=message)

        except (SyntaxError, ValueError) as e:
            # Raised if the load_json didn't succeed
            self.log.error("Protocol error on incoming message: {e}", e=e.message)
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
            return self.handleResponse(message)

        # -- New incoming message:
        #
        #    Call the dispatcher with a copy of our message. Want the
        #    original message intact for the response to peer.
        defer = maybeDeferred(self.messageReceived, message.copy())

        # -- Setup filling in the message data from the result
        def msg_ok(result):
            message.set_success(result)
            self.log.debug('{_cmdok}', cmdok=message)
            return result

        def msg_error(failure):
            message.set_fail(failure)

            # Accept the exception if listed in validNodeExceptions.
            for exc in VALID_NODE_EXCEPTIONS:
                if failure.check(exc):
                    return None

            # Print the error and dump the traceback
            self.log.error('REQUEST FAILED: {tb}', tb=failure.getTraceback())

            # Eat the error message
            return None

        def msg_timeout():
            ''' Response if command suffers a timeout '''
            exc = TimeoutException()
            message.set_fail(exc)
            self.log.error('REQUEST TIMED OUT')
            defer.errback(exc)

        # -- Setup a timeout, and add a timeout err handler making sure the
        #    message data failure is properly set
        add_defer_timeout(self.master.reactor, defer, self.command_timeout, msg_timeout)

        defer.addCallback(msg_ok)
        defer.addErrback(msg_error)

        # If requestid is set, the caller expects a reply.
        if message.requestid is not None:

            # Send response back to sender when the defer object fires
            defer.addBoth(lambda r, c: self.send(c), message)


    def handleResponse(self, message):
        ''' Handle the incoming response to a previous request. '''

        # Not much to do if we are not expecting a reply. I.e. the deferred
        # has already fired.
        if message.requestid not in self.requests:
            self.log.error("Dropping unexpeced response. "
                           "Late reply from a previous timed out request?")
            return

        # Get orginial request and delete it from the queue.
        request = self.requests.pop(message.requestid)
        #self.log.debug("       ^^ is a reply to {re}", re=request)

        # Link the request with the response by copying the
        # received data into the request. Args isn't needed any more
        request.response = message.response
        request.result = message.result

        # Get the defer handler and remove it from the request to prevent
        # calling it twice. Delete other modification from the request object
        defer = request.defer
        del request.defer
        request.requestid = None
        #request.args = None  # Might not be a good idea to remove the args
                              # from the request since ideally the the original
                              # request should be intact.

        # -- Remote request successful
        if message.response:

            # Send successful result back
            self.log.debug('{_cmdok}', cmdok=request)
            if not defer.called:

                # Been back and forth between sending 'request' or
                # 'request.result' back to the caller. When run_command() is
                # called, if the command returns immediately an immediate result
                # is returned. If run_command() returns a Deferred(), the object
                # sent back from here will be the object the caller receives.
                # If the 'request' object is sent back, the caller receives the
                # request object and not the result, which breaks the logic
                # from the direct, non-Deferred(), result.
                # On the other hand, since the run_command() parameter is a
                # Message(), then it can be argued that the response should
                # be the the request object.
                # In all cases the caller's request object will contain the
                # result of the command. So I think the best solution is to send
                # back the result, and rather let the caller use the request
                # object if needed.
                #
                # The choice here is also linked to the response in
                # Responder.run_commandlist()
                #
                defer.callback(request.result)
                #defer.callback(request)
            else:
                self.log.error('Dropping callback as defer has already been called. Timeout?')

        # -- Remote request failed
        else:

            def response_error(failure):  # pylint: disable=W0613
                # Print the error
                #self.log.error('{tb}', tb=failure.getTraceback())

                # Eat the error message
                return None

            # Add an eat-error message to the end of the chain
            defer.addErrback(response_error)

            # Send an error back
            exc = NodeException(*request.result)
            self.log.error('{_cmderr}', cmderr=request)
            if not defer.called:
                defer.errback(exc)
            else:
                self.log.error('Dropping errback as defer has already been called. Timeout?')


    def messageReceived(self, message):
        ''' Process an incoming message. This method should return
            a Deferred() if results are not immediately available
        '''
        raise UnknownMessageException(message.name)


    def send(self, message):
        ''' Send a message to the peer. A Deferred() object is returned if
            the message requires a response from peer.
        '''

        # -- Generate deferred and setup timeout if this is a new command
        #    to send (case b)
        defer = None
        if message.want_response and message.requestid is None:
            # If want_response=True and requestid is set, then this
            # is is the response.

            # -- Generate a deferred object
            message.defer = defer = Deferred()

            def send_timeout(message):
                ''' Failure if remote command suffers a timeout '''
                self.link.set_YELLOW('Communication timeout')
                self.requests.pop(message.requestid)
                exc = TimeoutException()
                message.set_fail(exc)
                message.defer.errback(exc)

            # -- Setup a timeout, and add a timeout err handler making sure the
            #    message data failure is properly set
            add_defer_timeout(self.master.reactor, defer, self.remote_timeout,
                              send_timeout, message)

            # -- Generate new requestid for message, save message in request list
            self.requests[message.get_requestid()] = message

        # -- Encode and send the command
        self.log.debug('{_cmdout}', cmdout=message)
        data = message.dump_json()
        self.log.debug('{_rawout}', rawout=data)
        self.transport.write(data+'\n')

        return defer

# -*- python -*-
from __future__ import absolute_import

from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet.defer import Deferred, CancelledError, maybeDeferred
from twisted.python.log import addObserver, removeObserver

from lumina.plugin import Plugin
from lumina.event import Event
from lumina.exceptions import *
from lumina.log import Logger
from lumina import utils
from lumina.state import ColorState


# FIXME: Add this as a config statement
DEFAULT_TIMEOUT = 10


# Valid exceptions that we can receive from the client/leaf. All other exception
# types will be mapped to ClientException()
#validClientExceptions = (
#    #CommandException,
#    CommandRunException,
#    UnknownCommandException,
#    TimeoutException,
#)

# To connect interactively to the server use:
#    socat - TCP:127.0.0.1:8081
# and send '***' to enable interactive mode


class ServerProtocol(LineReceiver):
    noisy = False
    delimiter = '\n'
    timeout = DEFAULT_TIMEOUT


    def __init__(self, parent):
        self.parent = parent
        self.servername = parent.name
        self.log = Logger(namespace=self.servername)


    def connectionMade(self):
        (h,p) = (self.transport.getPeer().host,self.transport.getPeer().port)
        self.ip = "%s:%s" %(h,p)
        self.log.namespace = self.servername + ':' + self.ip
        self.name = self.ip
        self.hostname = h
        self.events = []
        self.commands = []
        self.requests = { }
        self.interactive = False
        self.observer = None
        self.log.info("Connect from {ip}", ip=self.ip, system=self.servername)

        # Inform parent class
        self.parent.connectionMade(self)


    def connectionLost(self, reason):
        self.log.info("Lost connection from '{n}' ({ip})", n=self.name, ip=self.ip)

        if len(self.events):
            self.log.info("De-registering {n} events", n=len(self.events))
            # FIXME: Handle exceptions from parent
            self.parent.remove_events(self.events)

        if len(self.commands):
            self.log.info("De-registering {n} commands", n=len(self.commands))
            # FIXME: Handle exceptions from parent
            self.parent.remove_commands(self.commands)

        self.events = []
        self.commands = []
        if self.interactive:
            #removeObserver(self.interactive_logger)
            self.interactive = False

        # Cancel any pending requests
        for (seq,request) in self.requests.items():
            self.connectionLostResponse(request)

        # Inform parent class
        self.parent.connectionLost(self)


    def lineReceived(self, data):

        # Process the incoming data
        self.processData(data)

        # Interactive prompt
        if self.interactive:
            self.transport.write('lumina> ')


    def processData(self, data):
        ''' Handle messages from the clients '''

        # -- Empty lines are simply ignored
        if not len(data):
            return

        self.log.debug('', rawin=data)

        # -- Special *** notation which puts the session into interactive mode
        if data.startswith('***'):
            self.interactive = True
            #addObserver(self.interactive_logger)
            self.log.info("Starting interactive mode")
            return

        # -- Parse the incoming message as an Event
        try:
            if not self.interactive:
                # Load JSON in non-interactive mode
                event = Event().load_json(data)
            else:
                # Load string mode with shell-like parsing in interactive mode
                event = Event().load_str(data,shell=True)
            self.log.debug('', cmdin=event)

        except (SyntaxError,ValueError) as e:
            # Raised if the parsing didn't succeed
            self.log.error("Protcol error on incoming message: {m}", m=e.message)
            return

        # -- Interactive handler
        if self.interactive:
            if self.processInteractive(event) is None:
                return

        # -- Register client name
        if event.name == 'name':
            self.name = event.args[0]
            self.log.namespace = self.servername + ':' + event.args[0]
            self.log.info("Registering client {n} ({ip})", n=event.args[0], ip=self.ip)
            return

        # -- Register host name
        #elif event.name == 'hostname':
        #    self.log.info('Client {h} is named {n}', h=self.hostname, n=event.args[0])
        #    self.hostname = event.args[0]
        #    return

        # -- Register client events
        elif event.name == 'events':
            evlist = [ self.name + '/' + e for e in event.args ]
            if len(evlist):
                self.log.info("Registering {n} events", n=len(evlist))
                self.events = evlist
                # FIXME: Handle exceptions from parent
                self.parent.add_events(evlist)
            return

        # -- Register client commands
        elif event.name == 'commands':
            evlist = [ self.name + '/' + e for e in event.args ]
            if len(evlist):
                self.log.info("Registering {n} commands", n=len(evlist))
                self.commands = evlist
                # FIXME: Handle exceptions from parent
                self.parent.add_commands({ e: self.send for e in evlist})
            return

        # -- Handle 'exit' event
        elif event.name == 'exit':
            self.transport.loseConnection()
            return

        # -- Handle a reply to a former command
        elif event.seq in self.requests:

            # Copy received data into request
            request = self.requests.pop(event.seq)
            request.success = event.success
            request.result = event.result

            # Rewrite the event to name/event before sending to the handler
            request.name = self.name + '/' + event.name

            # Take the defer handler and remove it from the request to prevent calling it twice
            (defer, request.defer) = (request.defer, None)

            if event.success:

                # Send successful result back
                self.log.info('', cmdok=request)
                defer.callback(request)
            else:

                # Send an error back
                exc = ClientException(*request.result)
                self.log.error('', cmderr=request)
                defer.errback(exc)

            return

        # -- A new incoming (async) event.
        else:
            # Rewrite the event to name/event before sending to the handler
            event.name = self.name + '/' + event.name

            if event.name not in self.events:
                self.log.error("Ignoring unknown event '{e}'", e=event)
                return

            try:
                d=self.parent.handle_event(event)
                
                # Slurp failure from running the event, but pass others
                if d:
                    d.addErrback(lambda r: r.trap(CommandRunException) )

            # Any error at this point should be on the server's own accord and should not
            # affect the client connection, so this except is required
            except Exception as e:
                self.log.failure("Failed to process event '{e}'", e=event)
                return


    def connectionLostResponse(self, event):
        ''' Response if connection are lost during connection '''
        exc = LostConnectionException()
        event.set_fail(exc)
        event.defer.errback(exc)


    def timeoutResponse(self, event):
        ''' Response if command suffers a timeout '''
        exc = TimeoutException()
        event.set_fail(exc)
        event.defer.errback(exc)


    # -- Send a command to the client
    def send(self, event):
        # -- Remove the 'name/' prefix
        prefix = self.name + '/'
        event.name = event.name.replace(prefix, '')

        # -- Generate a deferred object
        event.defer = d = Deferred()

        # -- Setup a timeout, and add a timeout err handler making sure the event data failure
        #    is properly set
        timer = utils.add_defer_timeout(d, self.timeout, self.timeoutResponse, event)

        # FIXME: Add transform functions for changing ClientException() into other
        #        exception types?

        # -- Generate new seq for request, save it in request list and setup for
        #    it to be deleted when the deferred object fires
        event.gen_seq()
        self.requests[event.seq] = event

        # -- Encode and send the command
        self.log.debug('', cmdout=event)
        data=event.dump_json()
        self.log.debug('', rawout=data)
        self.transport.write(data+'\n')

        return d


    # -- INTERACTIVE mode
    def processInteractive(self, event):

        write = self.transport.write
        def reply(data):
            write(('>>>  ' + data + '\n').encode('UTF-8'))
        def raw_reply(result,event):
            reply("SUCCESS: %s" %(event))
        def raw_error(failure,event):
            reply("FAILED: %s: %s" %(event,failure.getErrorMessage()))
            # This will be reported as an unhandled error in Deferred unless we return
            # none here.
            return None

        cmd = event.name
        c = cmd[0]
        try:
            if c == '@':
                # Interpret as command
                event.name = cmd[1:]
                d=self.parent.run_command(event)
                d.addCallback(raw_reply, event)
                d.addErrback(raw_error, event)

            elif c == '*':
                # Interpret as event
                event.name = cmd[1:]
                d=self.parent.handle_event(event)
                if d:
                    d.addCallback(raw_reply, event)
                    d.addErrback(raw_error, event)                

            elif cmd == 'exit':
                self.transport.loseConnection()

            elif cmd == 'name':
                return True

            elif cmd == 'ls':
                # List
                if not len(event.args):
                    reply("%s: Too few arguments" %(cmd))
                elif event.args[0] == 'events':
                    l=self.parent.events[:]
                    l.sort()
                    reply("  ".join(l))
                elif event.args[0] == 'commands':
                    l=self.parent.commands.keys()
                    l.sort()
                    reply("  ".join(l))
                else:
                    reply("%s: Syntax error" %(cmd))

            # FIXME: Add other interactive commands here...

            else:
                reply("Unknown command '%s'" %(event.name))

        except Exception as e:
            # Handles any errors before the commands are run
            reply('ERROR: %s: %s' %(event, e.message))
            self.log.failure("Exception on {e}: {m}", e=event, m=e.message)


    def interactive_logger(self,msg):
        self.transport.write(('    [%s] %s\n' %(msg.get('log_system','-'),
                                                msg.get('log_text',''))).encode('UTF-8'))



class ServerFactory(Factory):
    noisy = False
    def __init__(self,parent):
        self.parent = parent
        self.name = parent.name
    def buildProtocol(self, addr):
        return ServerProtocol(parent=self.parent)
    def doStart(self):
        self.parent.status.set_YELLOW('Waiting for connections')
        Factory.doStart(self)
    def doStop(self):
        self.parent.status.set_OFF()
        Factory.doStop(self)



class Server(Plugin):
    ''' Lumina TCP server which serves as connection points for Leaf
        objects '''

    name = 'SERVER'

    CONFIG = {
        'port': dict( default=5326, help='Controller server port', type=int ),
    }


    def setup(self, main):
        # Setup logging and status
        self.log = Logger(namespace=self.name)
        self.status = ColorState(log=self.log)

        # Config options
        self.port = main.config.get('port',name=self.name)

        # List of commands and events
        self.events = []
        self.commands = {}

        # List of connected clients
        self.clients = []

        # Setup default do-nothing handler for the incoming events
        self.handle_event = lambda a : self.log.info("Ignoring event '{a}'", a=a)

        self.factory = ServerFactory(parent=self)
        reactor.listenTCP(self.port, self.factory)
        

    def run_command(self, event, fail_on_unknown=True):
        ''' Send a command to a client and return a deferred object for the reply '''

        # FIXME: Do we need the fail_on_unknown option?
        
        def unknown_command(event):
            exc = UnknownCommandException(event.name)
            event.set_fail(exc)
            if fail_on_unknown:
                self.log.error('', cmderr=event)
                raise exc
            self.log.warn("Ignoring unknown command: '{n}'", n=event.name)

        return maybeDeferred(self.commands.get(event.name, unknown_command), event)


    # --- INTERNAL COMMANDS
    def connectionMade(self, client):
        ''' Register the connected client '''
        self.clients.append(client)
        self.status.set_GREEN()


    def connectionLost(self, client):
        ''' Remove the disconnected client '''
        self.clients.remove(client)
        if not self.clients:
            self.status.set_YELLOW('No clients connected')


    def add_commands(self, commands):
        ''' Add to the dict of known commands and register their callback fns '''

        #self.log.debug("Registering {n} commands", n=len(commands))
        for name,fn in commands.items():
            if name in self.commands:
                raise TypeError("Command '{n}' already exists", n=name)
            self.commands[name] = fn


    def remove_commands(self, commands):
        ''' Remove from the dict of known commands '''

        #self.log.debug("De-registering {n} commands", n=len(commands))
        for name in commands:
            del self.commands[name]


    def add_events(self,events):
        ''' Add to the list of known events'''

        #self.log.debug("Registering {n} events", n=len(events))
        for name in events:
            if name in self.events:
                raise TypeError("Event '{n}' already exists", n=name)
            self.events.append(name)


    def remove_events(self, events):
        ''' Remove from the list of known events'''

        #self.log.debug("De-registering {n} events", n=len(events))
        for name in events:
            self.events.remove(name)


PLUGIN = Server

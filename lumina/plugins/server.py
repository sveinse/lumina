# -*- python -*-
from __future__ import absolute_import

from datetime import datetime

from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet.defer import Deferred, maybeDeferred
#from twisted.python.log import addObserver, removeObserver

from lumina.plugin import Plugin
from lumina.event import Event
from lumina.exceptions import (NodeException, NoConnectionException, TimeoutException,
                               NodeConfigException, UnknownCommandException)
from lumina.log import Logger
from lumina import utils
from lumina.state import ColorState


# FIXME: Add this as a config statement
DEFAULT_TIMEOUT = 10


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
        client_ip = self.transport.getPeer().host
        client_port = self.transport.getPeer().port
        self.ip = "%s:%s" %(client_ip, client_port)
        self.log.namespace = self.servername + ':' + self.ip
        self.log.info("Connect from {ip}", ip=self.ip, system=self.servername)

        # Node data
        self.name = self.ip
        self.nodeid = None
        self.hostname = client_ip
        self.hostid = None
        self.module = None
        self.status = 'OFF'
        self.status_why = 'No data received yet'
        self.lastactivity = datetime.utcnow()
        self.n_commands = 0
        self.n_events = 0

        self.events = []
        self.commands = []
        self.requests = {}
        self.interactive = False
        #self.observer = None

        # Inform parent class
        self.parent.add_node(self)


    def connectionLost(self, reason):
        self.log.info("Lost connection from '{n}' ({ip})", n=self.name, ip=self.ip)

        if self.interactive:
            #removeObserver(self.interactive_logger)
            self.interactive = False

        # Cancel any pending requests
        for (seq, request) in self.requests.items():
            self.connectionLostResponse(request)

        # Inform parent class
        self.parent.remove_node(self)


    def lineReceived(self, data):

        # Process the incoming data
        self.process_data(data)

        # Interactive prompt
        if self.interactive:
            self.transport.write('lumina> ')


    def process_data(self, data):
        ''' Handle messages from nodes '''

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
                event = Event().load_str(data, shell=True)
            self.log.debug('', cmdin=event)

        except (SyntaxError, ValueError) as e:
            # Raised if the parsing didn't succeed
            self.log.error("Protcol error on incoming message: {m}", m=e.message)
            return

        # -- Interactive handler
        if self.interactive:
            if self.processInteractive(event) is None:
                return

        # Update the activity timer
        self.lastactivity = datetime.utcnow()

        # -- Register node name
        if event.name == 'register':

            # Extract the data
            kw = event.kw
            self.name = kw.get('node', self.name)
            self.nodeid = kw.get('nodeid', self.nodeid)
            self.hostname = kw.get('hostname', self.hostname)
            self.hostid = kw.get('hostid', self.hostid)
            self.module = kw.get('module', self.module)
            self.events = kw.get('events', [])
            self.commands = kw.get('commands', [])

            # Register with the server
            self.parent.register_node(self)

            # Set logging name
            self.log.namespace = self.servername + ':' + self.name

            return

        # -- Handle status update
        elif event.name == 'status':
            self.status = event.args[0]
            self.status_why = event.args[2]
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
                exc = NodeException(*request.result)
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
                defer = self.parent.handle_event(event)

                # Slurp failure from running the event, but pass others
                if defer:
                    defer.addErrback(lambda r: r.trap(CommandRunException))

            # Any error at this point should be on the server's own accord and should not
            # affect the node connection, so this except is required
            except Exception as e:    # pylint: disable=W0703
                self.log.failure("Failed to process event '{e}'", e=event)
                return


    def connectionLostResponse(self, event):
        ''' Response if connection are lost during connection '''
        exc = NoConnectionException()
        event.set_fail(exc)
        event.defer.errback(exc)


    def timeoutResponse(self, event):
        ''' Response if command suffers a timeout '''
        exc = TimeoutException()
        event.set_fail(exc)
        event.defer.errback(exc)


    # -- Send a command to the node
    def send(self, event):
        # -- Remove the 'name/' prefix
        prefix = self.name + '/'
        event.name = event.name.replace(prefix, '')

        # -- Generate a deferred object
        event.defer = defer = Deferred()

        # -- Setup a timeout, and add a timeout err handler making sure the event data failure
        #    is properly set
        utils.add_defer_timeout(defer, self.timeout, self.timeoutResponse, event)

        # FIXME: Add transform functions for changing NodeException() into other
        #        exception types?

        # -- Generate new seq for request, save it in request list and setup for
        #    it to be deleted when the deferred object fires
        event.gen_seq()
        self.requests[event.seq] = event

        # -- Encode and send the command
        self.log.debug('', cmdout=event)
        data = event.dump_json()
        self.log.debug('', rawout=data)
        self.transport.write(data+'\n')

        return defer


    # -- INTERACTIVE mode
    def processInteractive(self, event):

        write = self.transport.write
        def reply(data):
            write(('>>>  ' + data + '\n').encode('UTF-8'))
        def raw_reply(result, event):
            reply("SUCCESS: %s" %(event))
        def raw_error(failure, event):
            reply("FAILED: %s: %s" %(event, failure.getErrorMessage()))
            # This will be reported as an unhandled error in Deferred unless we return
            # none here.
            return None

        cmd = event.name
        c = cmd[0]
        try:
            if c == '@':
                # Interpret as command
                event.name = cmd[1:]
                defer = self.parent.run_command(event)
                defer.addCallback(raw_reply, event)
                defer.addErrback(raw_error, event)

            elif c == '*':
                # Interpret as event
                event.name = cmd[1:]
                defer = self.parent.handle_event(event)
                if defer:
                    defer.addCallback(raw_reply, event)
                    defer.addErrback(raw_error, event)

            elif cmd == 'exit':
                self.transport.loseConnection()

            elif cmd == 'name':
                return True

            elif cmd == 'ls':
                # List
                if not len(event.args):
                    reply("%s: Too few arguments" %(cmd))
                elif event.args[0] == 'events':
                    reply("  ".join(sorted(self.parent.events[:])))
                elif event.args[0] == 'commands':
                    reply("  ".join(sorted(self.parent.commands.keys())))
                else:
                    reply("%s: Syntax error" %(cmd))

            # FIXME: Add other interactive commands here...

            else:
                reply("Unknown command '%s'" %(event.name))

        except Exception as e:     # pylint: disable=W0703
            # Ensures commands never fail.
            # Handles any errors before the commands are run
            reply('ERROR: %s: %s' %(event, e.message))
            self.log.failure("Exception on {e}: {m}", e=event, m=e.message)


    def interactive_logger(self, msg):
        self.transport.write(('    [%s] %s\n' %(msg.get('log_system', '-'),
                                                msg.get('log_text', ''))).encode('UTF-8'))



class ServerFactory(Factory):
    noisy = False
    def __init__(self, parent):
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
    ''' Lumina node server.
    '''

    name = 'SERVER'

    CONFIG = {
        'port': dict(default=5326, help='Controller server port', type=int),
    }


    def setup(self, main):
        # Setup logging and status
        self.log = Logger(namespace=self.name)
        self.status = ColorState(log=self.log)

        # Config options
        self.port = main.config.get('port', name=self.name)

        # Store name for main instance. Used by web and admin to retrieve
        #self.hostname = main.hostname
        #self.hostid = main.hostid

        # List of commands and events
        self.events = []
        self.commands = {}

        # List of connected nodes
        self.nodes = []
        self.sequence = 0

        # Setup default do-nothing handler for the incoming events
        self.handle_event = lambda a: self.log.info("Ignoring event '{a}'", a=a)

        self.factory = ServerFactory(parent=self)
        reactor.listenTCP(self.port, self.factory)


    def run_command(self, event, fail_on_unknown=True):
        ''' Send a command to a node and return a deferred object for the reply '''

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
    def add_node(self, node):
        ''' Register the connected node '''
        self.sequence += 1
        node.sequence = self.sequence
        self.nodes.append(node)
        self.status.set_GREEN('%s nodes connected' %(len(self.nodes)))


    def remove_node(self, node):
        ''' Remove the disconnected node '''
        self.nodes.remove(node)
        if not self.nodes:
            self.status.set_YELLOW('No nodes connected')
        else:
            self.status.set_GREEN('%s nodes connected' %(len(self.nodes)))

        if node.events:
            self.log.info("De-registering {n} events", n=len(node.events))
            self.remove_events(node.events)

        if node.commands:
            self.log.info("De-registering {n} commands", n=len(node.commands))
            self.remove_commands(node.commands)


    def register_node(self, node):
        ''' Check and register a node. '''

        self.log.info("Registering node {node} [{nodeid}], "
                      "type {module}, host {hostname} [{hostid}], "
                      "{n_e} events, {n_c} commands from {ip}",
                      node=node.name,
                      nodeid=node.nodeid,
                      hostname=node.hostname,
                      hostid=node.hostid,
                      module=node.module,
                      ip=node.ip,
                      n_e=len(node.events),
                      n_c=len(node.commands))

        # -- Check the node id from the other nodes connected
        nodeid = node.nodeid
        nodelist = [n.nodeid == nodeid for n in self.nodes if n != node]
        if any(nodelist):
            self.log.warn("Node {n} [{id}] is already connected. "
                          "Possible reconnect", n=node.name, id=nodeid)

            # FIXME: disconnect the double node, because the name, event and
            #        commands probably fail to register.

        # -- Set the node name
        name = self.check_node_name(node, node.name)
        if name != node.name:
            self.log.warn("Node '{o}' is taken, renaming to '{n}'", o=node.name, n=name)
        node.name = name

        # -- Register node event
        evlist = [node.name + '/' + e for e in node.events]
        if evlist:
            self.log.info("Registering {n} events", n=len(evlist))
            node.events = tuple(evlist)
            self.add_events(evlist)

        # -- Register node commands
        evlist = [node.name + '/' + e for e in node.commands]
        if evlist:
            self.log.info("Registering {n} commands", n=len(evlist))
            node.commands = tuple(evlist)
            self.add_commands({e: node.send for e in evlist})


    def check_node_name(self, node, name):
        newname = name
        for count in range(1, 10):
            names = [n.name == newname for n in self.nodes if n != node]
            if not any(names):
                return newname
            newname = name + '_' + str(count)
        raise NodeConfigException("Unable to find appropriate name for '{o}'".format(o=name))


    def add_commands(self, commands):
        ''' Add to the dict of known commands and register their callback fns '''
        for name, fn in commands.items():
            if name in self.commands:
                raise NodeConfigException("Duplicate command '{n}'".format(n=name))
            self.commands[name] = fn


    def remove_commands(self, commands):
        ''' Remove from the dict of known commands '''
        for name in commands:
            del self.commands[name]


    def add_events(self, events):
        ''' Add to the list of known events'''
        for name in events:
            if name in self.events:
                raise NodeConfigException("Duplicate event '{n}'".format(n=name))
            self.events.append(name)


    def remove_events(self, events):
        ''' Remove from the list of known events'''
        for name in events:
            self.events.remove(name)


PLUGIN = Server

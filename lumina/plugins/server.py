# -*- python -*-
from __future__ import absolute_import

from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet.defer import Deferred,CancelledError,maybeDeferred
from twisted.python.log import addObserver,removeObserver

from ..plugin import Plugin
from ..event import Event
from ..exceptions import *
from ..log import *


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
    delimiter='\n'
    timeout=DEFAULT_TIMEOUT


    def __init__(self, parent):
        self.parent = parent
        self.serversystem = parent.system


    def connectionMade(self):
        (h,p) = (self.transport.getPeer().host,self.transport.getPeer().port)
        self.ip = "%s:%s" %(h,p)
        self.system = self.serversystem + ':' + self.ip
        self.name = self.ip
        self.hostname = h
        self.events = []
        self.commands = []
        self.requests = { }
        self.interactive = False
        self.observer = None
        log("Connect from %s" %(self.ip,), system=self.serversystem)


    def connectionLost(self, reason):
        log("Lost connection from '%s' (%s)" %(self.name,self.ip), system=self.system)
        #if len(self.events):
        #    log("De-registering %s events" %(len(self.events)), system=self.system)
        #    self.parent.remove_events(self.events)
        if len(self.commands):
            log("De-registering %s commands" %(len(self.commands)), system=self.system)
            # FIXME: Handle exceptions from parent
            self.parent.remove_commands(self.commands)
        self.events = []
        self.commands = []
        if self.interactive:
            removeObserver(self.interactive_logger)
            self.interactive = False
        # FIXME: Cancel all pending request?


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

        lograwin(data, system=self.system)

        # -- Special @ notation which makes the controller execute the incoming data as a command
        #if data.startswith('@') or data.startswith('*'):
        #    self.interactive(data)
        #    return
        if data.startswith('***'):
            self.interactive = True
            addObserver(self.interactive_logger)
            log("Starting interactive mode", system=self.system)
            return

        # -- Parse the incoming message as an Event
        try:
            if not self.interactive:
                # Load JSON in non-interactive mode
                event = Event().load_json(data)
            else:
                # Load string mode in interactive mode
                event = Event().load_str(data,shell=True)
            logdatain(event, system=self.system)

        except (SyntaxError,ValueError) as e:
            # Raised if the load_json didn't succeed
            err("Protcol error on incoming message: %s" %(e.message), system=self.system)
            return

        # -- Interactive handler
        if self.interactive:
            if self.processInteractive(event) is None:
                return

        # -- Register client name
        if event.name == 'name':
            self.name = event.args[0]
            self.system = self.serversystem + ':' + event.args[0]
            log("***  Registering client %s (%s)" %(event.args[0],self.ip), system=self.system)
            return

        # -- Register host name
        elif event.name == 'hostname':
            log('***  Client %s is named %s' %(self.hostname,event.args[0]), system=self.system)
            self.hostname = event.args[0]
            return

        # -- Register client events
        elif event.name == 'events':
            evlist = [ self.name + '/' + e for e in event.args ]
            if len(evlist):
                log("Registering %s events" %(len(evlist)), system=self.system)
                self.events = evlist
                #self.parent.add_events(evlist)
            return

        # -- Register client commands
        elif event.name == 'commands':
            evlist = [ self.name + '/' + e for e in event.args ]
            if len(evlist):
                log("Registering %s commands" %(len(evlist)), system=self.system)
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

            # Rewrite the event to name/event before sending to the handler
            event.name = self.name + '/' + event.name

            # Copy received data into request
            request = self.requests.pop(event.seq)
            request.success = event.success
            request.result = event.result

            if event.success:

                # Send successful result back
                logcmdok(request, system=self.system)
                request.defer.callback(request)
            else:

                # Send an error back
                exc = ClientException(*request.result)
                logcmderr(request, system=self.system)
                request.defer.errback(exc)

            return

        # -- A new incoming (async) event.
        else:
            # Don't add the client/leaf name in interactive mode, enables sending any
            # events. Likewise, allow sending non-registered events.
            if not self.interactive:

                # Rewrite the event to name/event before sending to the handler
                event.name = self.name + '/' + event.name

                if event.name not in self.events:
                    err("Ignoring unknown event '%s'" %(event), system=self.system)
                    return

            try:
                self.parent.handle_event(event)

            # Any error at this point should be on the server's own accord and should not
            # affect the client connection, so this except is required
            except Exception as e:
                exclog("Failed to process event '%s'." %(event), system=self.system)
                return



    # -- Send a command to the client
    def send(self, event):
        # -- Remove the 'name/' prefix
        prefix = self.name + '/'
        event.name = event.name.replace(prefix, '')

        # -- Generate a deferred object
        event.defer = d = Deferred()

        # -- Setup a timeout
        timer = reactor.callLater(self.timeout, d.cancel)

        def timeout_transform(failure,event):
            ''' Transform a CancelledError, issued by Deferred.cancel(), into a TimeoutException '''
            failure.trap(CancelledError)
            exc = TimeoutException()
            event.set_fail(exc)
            raise exc

        def timeout_cancel(result):
            ''' Stop the timer if it has not been fired '''
            if timer.active():
                timer.cancel()
            return result

        d.addErrback(timeout_transform,event)
        d.addBoth(timeout_cancel)

        # FIXME: Add transform functions for changing ClientException() into other
        #        exception types?

        # -- Generate new seq for request, save it in request list and setup for
        #    it to be deleted when the deferred object fires
        event.gen_seq()
        self.requests[event.seq] = event

        # -- Encode and send the command
        logdataout(event, system=self.system)
        data=event.dump_json()
        lograwout(data, system=self.system)
        self.transport.write(data+'\n')

        return d


    # -- INTERACTIVE mode
    def processInteractive(self, event):

        write = self.transport.write
        def reply(data):
            write('>>>  ' + data + '\n')
        def raw_reply(reply,cls,event):
            if not isinstance(reply.success,bool):
                (result,reply.result)=(reply.result,'(...)')
                for r in result:
                    cls.transport.write("     %s\n" %(str(r),))
            reply(str(reply))
        def raw_error(failure,cls,event):
            reply("%s FAILED: %s %s\n" %(
                event.name,failure.value.__class__.__name__,str(failure.value)))

        cmd = event.name
        c = cmd[0]
        try:
            if c == '@':
                # Interpret as command
                event.name = cmd[1:]
                d=self.parent.run_command(event)
                d.addCallback(raw_reply, self, event)
                d.addErrback(raw_error, self, event)
                return

            elif c == '*':
                # Interpret as event, continue calling function by returning True
                event.name = cmd[1:]
                return True

            elif cmd == 'exit':
                return True
            elif cmd == 'name':
                return True

            # FIXME: Add other interactive commands here...

            else:
                reply("Unknown command '%s'" %(event.name))

        except Exception as e:
            # Handles any errors before the commands are run
            reply('%s ERROR: %s\n' %(event,e.message))


    def interactive_logger(self,msg):
        self.transport.write(('    [%s] %s\n' %(msg['log_system'],msg['log_text'])).encode('UTF-8'))


class ServerFactory(Factory):
    noisy = False
    def __init__(self,parent):
        self.parent = parent
        self.system = parent.system
    def buildProtocol(self, addr):
        return ServerProtocol(parent=self.parent)



class Server(Plugin):
    name = 'SERVER'

    CONFIG = {
        'port': dict( default=8081, help='Controller server port', type=int ),
    }


    def setup(self, main):
        # Set logging system name
        self.system = self.name

        self.port = main.config.get('port',name=self.system)
        #self.events = {}
        self.commands = {}

        # Setup default do-nothing handler for the incoming events
        self.handle_event = lambda a : log("Ignoring event '%s'" %(a), system=self.system)

        self.factory = ServerFactory(parent=self)
        reactor.listenTCP(self.port, self.factory)


    def run_command(self, event, fail_on_unknown=True):
        ''' Send a command to a client and return a deferred object for the reply '''

        def unknown_command(event):
            exc = UnknownCommandException(event.name)
            event.set_fail(exc)
            if fail_on_unknown:
                err("Unknown command: '%s'" %(event.name), system=self.system)
                raise exc
            log("Ignoring unknown command: '%s'" %(event.name), system=self.system)

        return maybeDeferred(self.commands.get(event.name, unknown_command), event)


    # --- COMMANDS
    def add_commands(self, commands):
        ''' Add to the dict of known commands and register their callback fns '''

        log("Registering %s commands" %(len(commands),), system=self.system)
        for name,fn in commands.items():
            if name in self.commands:
                raise TypeError("Command '%s' already exists" %(name))
            self.commands[name] = fn


    def remove_commands(self, commands):
        ''' Remove from the dict of known commands '''

        log("De-registering %s commands" %(len(commands),), system=self.system)
        for name in commands:
            if name not in self.commands:
                raise TypeError("Unknown command '%s'" %(name))
            del self.commands[name]


    # --- EVENTS
    #def add_events(self,events):
    #    ''' Add to the list of known events'''

    #    if isinstance(events, dict):
    #        events=events.keys()

    #    #log("Registering %s events" %(len(events),), system=self.system)
    #    for name in events:
    #        if name in self.events:
    #            raise TypeError("Event '%s' already exists" %(name))
    #        self.events.append(name)

    #def remove_events(self, events):
    #    ''' Remove from the list of known events'''

    #    #log("De-registering %s events" %(len(events),), system=self.system)
    #    for name in events:
    #        if name not in self.events:
    #            raise TypeError("Unknown event '%s'" %(name))
    #        self.events.remove(name)


PLUGIN = Server

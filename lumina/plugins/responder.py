# -*- python -*-
from __future__ import absolute_import

from twisted.internet.defer import Deferred

from lumina.event import Event
from lumina.plugin import Plugin
from lumina.exceptions import CommandParseException, ConfigException, CommandRunException

# Import responder rules from separate file
from lumina.plugins.rules import alias, responses


# FIXME: Add this as config statements
MAX_DEPTH = 10
DEFAULT_TIMEOUT = 10



class Responder(Plugin):
    ''' Handles events from nodes and reacts to
        them with programmable rules.
    '''

    def setup(self, main):
        Plugin.setup(self, main)

        self.alias = alias.copy()
        self.responses = responses.copy()

        self.server = server = main.get_plugin_by_module('server')
        if not server:
            raise ConfigException('No server plugin found. Missing server in config?')

        # Patch the server's handle event to this handler
        server.handle_event = self.handle_event

        # Register the aliases as commands. Note that get_commandfnlist() below
        # depends on that the handler for the commands are self.run_command
        server.add_commands({a: self.run_command for a in self.alias})

        # This plugin does not have active statuses
        self.status.set_GREEN()


    def handle_event(self, event):
        ''' Respond to the received event '''

        # Find the job for the given event
        job = self.responses.get(event.name, None)
        if job is None:
            self.log.info("Ignoring event '{e}'", e=event)
            #self.log.info("  --:  Ignored",)
            return None

        # Make a job object and its parse args and run it
        #self.log.debug("Event '{e}' received", e=event)
        command = Event().load_str(job, parse_event=event)
        self.log.info("Event '{e}' -> '{c}'", e=event, c=command)
        return self.run_command(command)


    def run_command(self, command):
        self.log.info("  --:  Running '{c}'", c=command)
        return self.run_commandlist(command, self.get_commandlist(command))


    def get_commandlist(self, command, depth=0):
        ''' Get a list of (fn,event) tuples for the given command (Event() object
            expected '''

        # Get the function for the given command. Return None if no command exists
        fn = self.server.commands.get(command.name)

        # If the function is this run_command() function, it indicates that the function
        # is an alias that needs to be expanded. Else this is a function that should be
        # called normally.
        if fn != self.run_command:
            return [command]

        # ...the returned object is a composite and needs to be flattened/expanded

        # Make sure this function isn't run too many times in case of loops in
        # the aliases
        if depth >= MAX_DEPTH:
            raise CommandParseException('Too many command alias levels (%s). Loop?' %(depth,))

        # Get the alias list for the command and flatten it
        commandlist = []
        for cmd in self.alias[command.name]:

            # Convert the string alias to Event() object
            try:
                event = Event().load_str(cmd, parse_event=command)
            except Exception as e:
                raise CommandParseException("Command parsing failed: %s" %(e))
            #ev.system = command.system   # To override log system

            # Iterate over the found commands to check if they too are aliases
            commandlist += self.get_commandlist(event, depth=depth+1)

        return commandlist


    def run_commandlist(self, command, commandlist): #, timeout=DEFAULT_TIMEOUT):
        ''' Run the commandlist (which should be an Event object) '''

        # Print the events
        self.log.info("  --:    {l}", l=commandlist)

        # If the command and the commandlist contains the same command (which happens
        # if you call self.run_command() on a non-composite alias command), then
        # simply call it as an ordinary command
        if len(commandlist) == 1 and id(command) == id(commandlist[0]):
            return self.server.run_command(command)

        # Helper-class for executing the command-list
        class RunCommandList(object):
            def __init__(self, command, commandlist, log):
                self.log = log
                self.defer = Deferred()
                self.request = command
                self.commandlist = commandlist
                self.remain = len(commandlist)
                self.failed = []
                self.success = 0

            def execute(self, server):

                # Null-lengthed commandlists must be completed by manually calling the
                # dispatch handler.
                if self.remain == 0:
                    self.cmd_done(None)

                else:
                    # Execute all of the commands in the commandlist
                    for cmd in self.commandlist:

                        # Attach callbacks to handle progress
                        defer = server.run_command(cmd)
                        defer.addCallback(self.cmd_ok, cmd)
                        defer.addErrback(self.cmd_err, cmd)
                        defer.addBoth(self.cmd_done)

                        # ...the local defer object is not needed by anyone else...

                return self.defer

            def cmd_ok(self, result, cmd):
                self.success += 1
                return result

            def cmd_err(self, failure, cmd):
                self.failed.append(cmd)
                return failure

            def cmd_done(self, result):
                self.remain -= 1
                # Done?
                if self.remain <= 0:
                    # Prepare the response
                    request = self.request
                    request.result = self.commandlist
                    request.success = self.success

                    # Success is when all sub-jobs succeeds
                    if self.success == len(self.commandlist):
                        self.log.info('', cmdok=request)
                        self.defer.callback(request)

                    else:
                        self.log.error('{_cmderr}, {f}/{n} succeeded',
                                       cmderr=request, f=self.success,
                                       n=len(self.commandlist))
                        self.defer.errback(CommandRunException(request))

                # We want to accept the fault/error
                return None

        rundata = RunCommandList(command=command, commandlist=commandlist, log=self.log)
        return rundata.execute(self.server)



PLUGIN = Responder

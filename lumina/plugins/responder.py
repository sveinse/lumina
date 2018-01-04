# -*- python -*-
""" Main execution plugin for responding to events and logic """
from __future__ import absolute_import

from twisted.internet.defer import Deferred, maybeDeferred

from lumina.message import Message
from lumina.plugin import Plugin
from lumina.exceptions import CommandParseException, ConfigException, CommandRunException
from lumina.lumina import master



class Responder(Plugin):
    ''' Handles events from nodes and reacts to
        them with programmable rules.
    '''

    CONFIG = {
        'actions': dict(default={}, help='List of reponses to incoming events', type=dict),
        'groups': dict(default={}, help='List of groups of commands', type=dict),
        'max_depth': dict(default=10, help='Maxium nesting depth of recursive groups', type=int),
    }

    DEPENDS = ('server',)


    def setup(self):

        self.groups = master.config.get('groups', name=self.name).copy()
        self.actions = master.config.get('actions', name=self.name).copy()
        self.max_depth = master.config.get('max_depth', name=self.name)

        # If any items in the actions list contains a list, make it into
        # a group with name '__<name>'
        for k, v in self.actions.items():
            if not isinstance(v, list):
                continue
            n = '__' + k
            self.groups[n] = v
            self.actions[k] = n

        self.server = server = master.get_plugin_by_module('server')
        if not server:
            raise ConfigException('No server plugin found. Missing server in config?')

        # Patch the server's handle event to this handler
        server.handle_event = self.handle_event

        # Register the group items as commands. Note that get_commandfnlist() below
        # depends on that the handler for the commands are self.run_command
        server.add_commands({a: self.run_command for a in self.groups})

        # Ready
        self.status.set_GREEN()


    def handle_event(self, message):
        ''' Respond to the received event '''

        # Find the action for the given event
        action = self.actions.get(message.name, None)
        if action is None:
            self.log.info("Ignoring event '{e}'", e=message)
            return None

        # Make a command and parse its args and run it
        command = Message.create('command').load_str(action, parse_event=message)
        self.log.info("Event '{e}' -> '{c}'", e=message, c=command)
        return self.run_command(command)


    def run_command(self, command):
        self.log.info("  --:  Running '{c}'", c=command)
        return self.run_commandlist(command, self.get_commandlist(command))


    def get_commandlist(self, command, depth=0):
        ''' Get a list of (fn,message) tuples for the given command (Message() object
            expected '''

        # Get the function for the given command. Return None if no command exists
        fn = self.server.commands.get(command.name)

        # If the function is this run_command() function, it indicates that the function
        # is an group that needs to be expanded. Else this is a function that should be
        # called normally.
        if fn != self.run_command:
            return [command]

        # ...the returned object is a composite and needs to be flattened/expanded

        # Make sure this function isn't run too many times in case of loops in
        # the groups
        if depth >= self.max_depth:
            raise CommandParseException('Too many command group levels (%s). Loop?' %(depth,))

        # Get the groups list for the command and flatten it
        commandlist = []
        for cmd in self.groups[command.name]:

            # Convert the string group-element to Event() object
            try:
                message = Message.create('command').load_str(cmd, parse_event=command)
            except Exception as e:
                raise CommandParseException("Command parsing failed: %s" %(e))
            #ev.system = command.system   # To override log system

            # Iterate over the found commands to check if they too are groups
            commandlist += self.get_commandlist(message, depth=depth+1)

        return commandlist


    def run_commandlist(self, command, commandlist):
        ''' Run the commandlist (which should be an Message object) '''

        # Print the events
        self.log.info("  --:    {l}", l=commandlist)

        # If the command and the commandlist contains the same command (which happens
        # if you call self.run_command() on a non-composite group command), then
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

                        # -- Attach callbacks to handle progress
                        defer = maybeDeferred(server.run_command, cmd)
                        defer.addCallback(self.cmd_ok, cmd)
                        defer.addErrback(self.cmd_err, cmd)
                        defer.addBoth(self.cmd_done)

                        # ...the local defer object is not needed by anyone else...

                return self.defer

            def cmd_ok(self, result, cmd):  # pylint: disable=unused-variable
                self.success += 1
                return result

            def cmd_err(self, failure, cmd):
                self.failed.append(cmd)
                return failure

            def cmd_done(self, result):  # pylint: disable=unused-variable
                self.remain -= 1
                # Done?
                if self.remain <= 0:
                    # Prepare the response
                    request = self.request
                    request.response = self.success

                    # Have been back and forth if the result list should be a
                    # list of the results or the actual command objects. The
                    # former fails to work when a command fails and the
                    # commands have only succeeded partially.
                    #request.result = [ c.result for c in self.commandlist ]
                    request.result = self.commandlist

                    # Success is when all sub-jobs succeeds
                    if self.success == len(self.commandlist):
                        self.log.info('{_cmdok}', cmdok=request)

                        # Likewise, if request.result is sent back, the list
                        # is sent without the request.response containing the
                        # number of successful commands.

                        self.defer.callback(request.result)
                        #self.defer.callback(request)

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

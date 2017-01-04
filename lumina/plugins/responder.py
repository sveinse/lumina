# -*- python -*-
from __future__ import absolute_import

from twisted.internet.defer import Deferred,DeferredList,maybeDeferred,CancelledError
from twisted.internet import reactor

from ..event import Event
from ..plugin import Plugin
from ..exceptions import *
from ..log import *

# Import responder rules from separate file
from .rules import alias,jobs


# FIXME: Add this as config statements
MAX_DEPTH = 10
DEFAULT_TIMEOUT = 10



class Responder(Plugin):
    name = 'RESPONDER'


    def setup(self, main):
        self.system = self.name

        self.alias = alias.copy()
        self.jobs = jobs.copy()

        self.server = server = main.get_plugin_by_module('server')
        if not server:
            raise ConfigException('No server plugin found. Missing server in config?')

        # Patch the server's handle event to this handler
        server.handle_event = self.run_job

        # Register the aliases as commands. Note that get_commandfnlist() below
        # depends on that the handler for the commands are self.run_command
        server.add_commands({a: self.run_command for a in self.alias})


    def run_job(self, event):
        ''' Run the job for the given event '''

        # Find the job for the given event
        job = self.jobs.get(event.name,None)
        if job is None:
            log("Ignoring event '%s'" %(event), system=self.system)
            log("  --:  Ignored", system=self.system)
            return

        # Make a job object and its parse args and run it
        #log("Event '%s' received" %(event), system=self.system)
        command = Event().load_str(job, parseEvent=event)
        log("Event '%s' -> '%s'" %(event,command), system=self.system)
        return self.run_command(command)


    def run_command(self, command):
        log("  --:  Running '%s'" %(command), system=self.system)
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
            return [ command ]

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
                ev = Event().load_str(cmd, parseEvent=command)
            except Exception as e:
                raise CommandParseException("Command parsing failed: %s" %(e) )
            #ev.system = command.system   # To override log system

            # Iterate over the found commands to check if they too are aliases
            commandlist += self.get_commandlist(ev,depth=depth+1)

        return commandlist


    def run_commandlist(self, command, commandlist): #, timeout=DEFAULT_TIMEOUT):
        ''' Run the commandlist (which should be an Event object) '''

        # We need at least one command to run.
        #if not len(commandlist):
        #    raise CommandRunException("'%s' error: Nothing to run" %(command.name))

        # Compile a list of all the events which is going to be run (for printing)
        log("  --:    %s" %(commandlist), system=self.system)
        if not ( len(commandlist)==1 and command.name == commandlist[0].name ):
            #command.result = None
            #else:
            command.result = commandlist
            command.success = False

        # Chain all commands into one deferred list
        s = self.server
        d = DeferredList([ s.run_command(cmd, fail_on_unknown=False) for cmd in commandlist ],
                         consumeErrors=True, fireOnOneErrback=True)

        def list_ok(result, command, commandlist):
            logcmdok(commandlist, system=self.system)
            # Update the success variable with the number of successful commands
            # if len(command.result) == command.success then all succeeded
            if not ( len(commandlist)==1 and command.name == commandlist[0].name ):
                command.success = [ c.success for c in commandlist ].count(True)
            return command

        def list_error(failure, command, commandlist):
            logcmderr(commandlist, system=self.system)
            # Update the success variable with the number of successful commands
            if not ( len(commandlist)==1 and command.name == commandlist[0].name ):
                command.success = [ c.success for c in commandlist ].count(True)

            # Report the actual error back to the caller
            return failure.value.subFailure

        d.addCallback(list_ok, command, commandlist)
        d.addErrback(list_error, command, commandlist)
        return d


PLUGIN = Responder

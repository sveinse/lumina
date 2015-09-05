# -*- python -*-
#
# 2015.04.05
# Notater:
#   - Bor man implementere linking til parent/mother objektet, slik at man f.eks. kan holde
#     metrics, som hvor mange ganger et event har blitt fyrt av?
#
from twisted.internet.defer import Deferred,DeferredList,maybeDeferred,CancelledError
from twisted.python import log
from twisted.internet import reactor

from types import *

from event import Event
from exceptions import *


MAX_DEPTH = 10
DEFAULT_TIMEOUT = 10


def unknown_command(command):
    ''' Callback for any unknown commands '''
    #log.msg("    %s: Ignoring unknown command" %(command), system=command.system)

    # FIXME: This command should use an exception type which will fail. CommandException
    # is a subtype of Command
    raise UnknownCommandException()


def empty_command(command):
    ''' Callback for any empty (None) commands '''
    log.msg("    %s: Ignoring empty command" %(command,), system=command.system)


def transform_timeout(failure):
    ''' Transform a CancelledError into a TimeoutException '''
    failure.trap(CancelledError)
    raise TimeoutException()


def list_ok(result, command, commandlist):
    #log.msg("LIST_OK")

    # If command is an alias or composite command, save the results in the
    # command object
    if not ( len(commandlist)==1 and command.name == commandlist[0].name ):
        command.success = [ c.success for c in commandlist ].count(True)

    # This is what we send back to the calling function
    return command


def list_error(failure, command, commandlist):
    #log.msg("LIST_ERROR")

    # Ensure the success count is updated on failing lists
    if not ( len(commandlist)==1 and command.name == commandlist[0].name ):
        command.success = [ c.success for c in commandlist ].count(True)

    # Report the actual error back to the caller
    return failure.value.subFailure



class Core(object):
    system='CORE'

    # Default configuration options
    CONFIG = { }


    def __init__(self):
        self.events = []
        self.commands = {}
        self.endpoints = []
        self.jobs = {}

        # Job handler
        self.queue = []
        self.currentjob = None
        self.inprogress = False
        self.currentcommand = None



    # --- EVENTS
    def add_events(self,events):
        ''' Add to the list of known events'''

        if isinstance(events, dict):
            events=events.keys()

        #log.msg("Registering %s events" %(len(events),), system=self.system)
        for name in events:
            if name in self.events:
                raise TypeError("Event '%s' already exists" %(name))
            self.events.append(name)

    def remove_events(self, events):
        ''' Remove from the list of known events'''

        #log.msg("De-registering %s events" %(len(events),), system=self.system)
        for name in events:
            if name not in self.events:
                raise TypeError("Unknown event '%s'" %(name))
            self.events.remove(name)


    # --- COMMANDS
    def add_commands(self, commands):
        ''' Add to the dict of known commands and register their callback fns '''

        #log.msg("Registering %s commands" %(len(commands),), system=self.system)
        for (name,fn) in commands.items():
            if name in self.commands:
                raise TypeError("Command '%s' already exists" %(name))
            self.commands[name] = fn

    def remove_commands(self, commands):
        ''' Remove from the dict of known commands '''

        #log.msg("De-registering %s commands" %(len(commands),), system=self.system)
        for name in commands:
            if name not in self.commands:
                raise TypeError("Unknown command '%s'" %(name))
            del self.commands[name]


    def run_command(self, command, timeout=DEFAULT_TIMEOUT):

        # Get the next command
        fn = self.get_commandfn(command)
        if not callable(fn):
            raise CommandRunException("%s lacks runnable function" %(command))

        # FIXME: Client commands must timeout in case the controller has lost
        #        interest in it.
        command.fn = fn
        return maybeDeferred(command.fn, command
                             ).addCallback(command.cmd_ok
                             ).addErrback(transform_timeout
                             ).addErrback(command.cmd_error)


    def run_commandlist(self, command, commandlist, timeout=DEFAULT_TIMEOUT):
        ''' Run the commandlist (which should be an Event object) '''

        # Compile a list of all the events which is going to be run (for printing)
        if not ( len(commandlist)==1 and command.name == commandlist[0].name ):
            log.msg("%s RUNS %s" %(command,commandlist), system=command.system)
            command.result = commandlist
        else:
            log.msg("RUN %s" %(commandlist), system=command.system)
            command.result = None

        # We need at least one command to run.
        #if not len(commandlist):
        #    raise CommandRunException("'%s' error: Nothing to run" %(command.name))

        #command.result = commandlist
        command.success = False

        # Call all of the commands.
        d = DeferredList([ maybeDeferred(cmd.fn,cmd
                                     ).addCallback(cmd.cmd_ok
                                     ).addErrback(transform_timeout
                                     ).addErrback(cmd.cmd_error)
                           for cmd in commandlist ],
                         consumeErrors=True, fireOnOneErrback=True)
        d.addCallback(list_ok, command, commandlist)
        d.addErrback(list_error, command, commandlist)
        command.timer = reactor.callLater(timeout, d.cancel)
        return d


    def get_commandfn(self, command):
        ''' Get the command function for the given command '''
        fn = self.commands.get(command.name, unknown_command)

        # Existing command, but with no fn handler
        if fn is None:
            fn = empty_command

        return fn


    def get_commandfnlist(self, command, depth=0):
        ''' Get a list of (fn,event) tuples for the given command (Event() object
            expected '''
        #log.msg("CCC ",depth,'.'*(depth+1),command,command.args)

        # If the function is callable, then this is the wanted dispatcher
        # for the command. Also return if the command is unknown or explicitly set
        # to None.
        fn = self.get_commandfn(command)
        if callable(fn):
            command.fn = fn
            #log.msg("=== ",depth,'.'*(depth+1),[ command ])
            return [ command ]

        # ...otherwise the returned object is a composite and needs to be flattened/expanded

        # Make sure this function isn't run too many times in case of loops in
        # the aliases
        if depth >= MAX_DEPTH:
            raise CommandRunException('Too many command alias levels (%s). Loop?' %(depth,))

        # Flatten the alias
        alias = list(fn[::-1])
        eventlist = []
        while len(alias):
            fn = alias.pop()

            # If callable alias, it is a function that will either return
            #    A) Another function, Event() or string object
            #    B) A list or tuple containing A)
            # The point is to enable aliases/composite commands to
            # pass on the argument from the original command
            # E.g.
            #       'command': ( lambda a: ('first', Event('second',a.args[0]), )
            if callable(fn):
                try:
                    alias.append(fn(command))
                except (KeyError,IndexError) as e:
                    raise CommandRunException(
                        "Alias function failed when processing '%s'. Missing argument?" %(
                        command.name,))

            # If list or tuple, expand the list and reiterate
            elif isinstance(fn, list) or isinstance(fn, tuple):
                alias += fn[::-1]

            # Append the Event object (or make one) to the eventlist
            elif isinstance(fn, Event):
                ev = fn.copy()
                ev.system = command.system
                eventlist.append(ev)
            else:
                ev = Event().load_str(fn)
                ev.system = command.system
                eventlist.append(ev)

        # eventlist is now a list of Event() objects. Let's iterate over the list
        # to compile a list of (fn,event) tuples.
        fnlist = []
        for f in eventlist:
            fnlist += self.get_commandfnlist(f,depth=depth+1)
        #log.msg("=== ",depth,'.'*(depth+1),fnlist)
        return fnlist


    # --- JOBS
    def add_jobs(self,jobs):
        ''' Add list of jobs '''

        log.msg("Registering %s handlers for events" %(len(jobs),), system=self.system)
        for (name,command) in jobs.items():
            if name in self.jobs:
                raise TypeError("Job '%s' already exists" %(name))
            self.jobs[name] = command


    def run_job(self,event):
        ''' Run the job for the given event '''

        name = self.jobs.get(event.name)
        if name is None:
            log.msg("     --:  Ignored", system='EVENT')
            return

        # Copy the original event, and parse in name and optional args from
        # the job
        job = event.copy()
        job.load_str(name)

        # Run it
        log.msg("     --:  Running %s" %(job,), system='EVENT')
        cmdlist = self.get_commandfnlist(job)
        return self.run_commandlist(job, cmdlist)

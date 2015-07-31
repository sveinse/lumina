# -*- python -*-
#
# 2015.04.05
# Notater:
#   - Bor man implementere linking til parent/mother objektet, slik at man f.eks. kan holde
#     metrics, som hvor mange ganger et event har blitt fyrt av?
#
from twisted.internet.defer import Deferred,DeferredList,maybeDeferred
from twisted.python import log
from twisted.internet import reactor

from types import *

from event import Event
from exceptions import *


MAX_DEPTH = 10


class Core(object):
    system='CORE'


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


    # --- ENDPOINT REGISTRATION
    def register(self,endpoint):
        log.msg("===  Registering endpoint %s" %(endpoint.name), system=self.system)
        endpoint.configure()
        endpoint.add_eventcallback(self.handle_event)
        self.add_events(endpoint.get_events())
        self.add_commands(endpoint.get_commands())
        endpoint.setup()
        reactor.addSystemEventTrigger('before','shutdown',endpoint.close)
        self.endpoints.append(endpoint)


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

    def get_commandfn(self, command):
        ''' Get the command handler function '''
        return self.commands.get(command)


    def run_command(self, command):
        ''' Run the command (which should be an Event object) '''

        # Get the list of commands to run
        fnlist = self.get_commandfnlist(command)
        #log.msg("RUN: ",fnlist,system=self.system)

        # Compile a list of all the events which is going to be run (for printing)
        if not ( len(fnlist)==1 and command.name == fnlist[0][1].name ):
            log.msg("%s RUNS %s" %(command,[ x[1] for x in fnlist ]), system='COMMAND')

        # Check if we have functions for all the events and make a list
        # of them to run.
        runlist = []
        err= []
        for (fn,ev) in fnlist:
            if fn is None:
                log.msg("    Unknown sub-command '%s'" %(ev.name,), system=self.system)
                err.append(ev.name)
            else:
                runlist.append( (fn,ev) )

        # We need at least one command to run.
        if not len(runlist):
            if len(err):
                raise CommandError("'%s' error: Unknown command(s): %s" %(command.name, err,))
            else:
                raise CommandError("'%s' error: Nothing to run" %(command.name))
        if len(err):
            log.msg("    ^^^ IGNORING unknown commands", system=self.system)

        # Call all of the commands.
        # NOTE: This runs ALL commands in parallell. No ordering.
        # FIXME: How to handle dependencies and/or serial execution?
        log.msg("RUN:  %s" %([ x[1] for x in runlist ]), system='COMMAND')
        deflist = [ maybeDeferred(x[0],x[1]) for x in runlist ]

        # One command to run? Then let's just return it
        if len(deflist) == 1:
            return deflist[0]

        # Otherwise make a composite which will fire when all of the deferreds have
        # fired
        d = DeferredList(deflist)
        return d


    def get_commandfnlist(self, command, depth=0):
        ''' Get a list of (fn,event) tuples for the given command (Event() object
            expected '''
        #log.msg("CCC ",depth,'.'*(depth+1),command,command.args)

        # If the function is callable, then this is the wanted dispatcher
        # for the command. Also return if fn is None, because that either means
        # no command registered with None function or no entry in list of commands.
        fn = self.commands.get(command.name)
        if fn is None or callable(fn):
            return [ (fn,command), ]
        elif fn is None:
            return [ ]

        # Make sure this function isn't run too many times in case of loops in
        # the aliases
        if depth > MAX_DEPTH:
            raise RuntimeError('Too many command alias levels (%s). Loop?' %(depth,))

        # The fn from commands is an alias, we need to flatten it
        alias = list(fn[::-1])
        eventlist = []
        while len(alias):
            fn = alias.pop()

            # If callable alias, it is a function that will either return
            #    A) Another function, Event() or string object
            #    B) A list or tuple containing A)
            # The point is to make it possible for alias/multiple commands to
            # pass on the argument from the original command
            if callable(fn):
                try:
                    alias.append(fn(command))
                except (KeyError,IndexError) as e:
                    raise CommandError("Alias function failed when processing '%s'. Missing argument?" %(command.name,))

            # If list or tuple, expand the list and reiterate
            elif isinstance(fn, list) or isinstance(fn, tuple):
                alias += fn[::-1]

            # Append the Event object (or make one) to the eventlist
            elif isinstance(fn, Event):
                eventlist.append(fn)
            else:
                eventlist.append(Event().parse_str(fn))

        # eventlist is now a list of Event() objects. Let's iterate over the list
        # to compile a list of (fn,event) tuples.
        fnlist = []
        for f in eventlist:
            fnlist += self.get_commandfnlist(f,depth=depth+1)
        return fnlist


    # --- JOBS
    def add_jobs(self,jobs):
        ''' Add list of jobs '''

        log.msg("Registering %s handlers for events" %(len(jobs),), system=self.system)
        for (name,command) in jobs.items():
            if name in self.jobs:
                raise TypeError("Job '%s' already exists" %(name))

            # This is done to allow job lists to be specified as text lists or lists
            #if isinstance(commands, JobBase):
            #    job = commands
            #else:
            #    job = Job( commands )
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
        job.parse_str(name)

        # Run it
        log.msg("     --:  Running %s" %(job,), system='EVENT')
        return self.run_command(job)

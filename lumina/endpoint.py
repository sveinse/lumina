#-*- python -*-

from callback import Callback
from event import Event
from twisted.python import log



class Endpoint(object):
    ''' Baseclass for endpoint functions '''

    cbevent = None
    events = { }
    commands = { }

    # --- Initialization
    def setup(self):
        pass
    def close(self):
        pass

    # --- Event handler
    def event(self, event, *args, **kw):
        if self.cbevent is not None:
            self.cbevent.callback(Event(event,*args,**kw))
    def add_eventcallback(self, callback, *args, **kw):
        if self.cbevent is None:
            self.cbevent = Callback()
        self.cbevent.addCallback(callback, *args, **kw)

    def event_as_arg(self, result, event, *args, **kw):
        ''' Can be used as deferred callbacks if it is wanted that the CB result
            becomes an argument.
                d.addCallback(event_as_arg,'some/event')
                d.callback('123')  # <-- Will result in some/event{123}
        '''
        if self.cbevent is not None:
            self.cbevent.callback(Event(event,result,*args,**kw))

    # --- Get list of events and commands
    def register(self):
        pass
    def get_events(self):
        return self.events
    def get_commands(self):
        return self.commands

    def get_command(self,command):
        return self.commands[command]


#-*- python -*-

from callback import Callback
from core import Event
from twisted.python import log



class Endpoint(object):
    ''' Baseclass for endpoint functions '''

    cbevent = None
    events = [ ]
    actions = { }

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

    # --- Get list of events and actions
    def get_events(self):
        return self.events
    def get_actions(self):
        return self.actions

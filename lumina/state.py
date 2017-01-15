#-*- python -*-
from __future__ import absolute_import

from lumina.log import Logger


# FIXME:  Useful States
#    init      startup state
#    idle      Waiting for activity (from lumina)
#    starting  starting up, connecting
#    ready     connected, waiting for inbound traffic
#    up        link is up
#    down      connection is down, closed
#    error     error state
#    halted    failed state


class State(object):
    ''' Class for keeping a state variable. States can be set using set(state, *args), and read
        with get(). It will log an entry when the state changes on set, and it can run a callback
        on changes.
    '''

    def __init__(self,state,log=None,change_callback=None,*args):
        self.state = state or 'init'
        if log is None:
            self.log = Logger()
        else:
            self.log = log
        self.args = args[:]
        self.change_callback = change_callback


    def set(self,state,*args):
        (old, self.state) = (self.state, state)
        self.args = args[:]
        s = ''
        if len(args):
            s = ' (%s)' %(",".join(args))
        if state != old:
            self.log.info('{_state}{extra}', state=(old,state), extra=s)

            if self.change_callback:
                self.change_callback(self.state, old, *args)


    def get(self):
        return self.state


    def is_in(self,*args):
        if self.state in args:
            return True
        return False

    def not_in(self,*args):
        return not self.is_in(*args)


    def set_DOWN(self,*args):
        self.set('down',*args)
    def set_ERROR(self,*args):
        self.set('error',*args)
    def set_IDLE(self,*args):
        self.set('idle',*args)
    def set_READY(self,*args):
        self.set('ready',*args)
    def set_STARTING(self,*args):
        self.set('starting',*args)
    def set_UP(self,*args):
        self.set('up',*args)

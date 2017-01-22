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

    def __init__(self,state=None,states=None,format=None,log=None,change_callback=None,why=None):
        self.state = state or 'init'
        if log is None:
            self.log = Logger()
        else:
            self.log = log
        self.states = states 
        self.format = format or {}
        self.why = why
        self.change_callback = change_callback


    def set(self,state,why=None):
        if self.states and state not in self.states:
            raise ValueError("Invalid state '%s'" %(state))
        (old, self.state) = (self.state, state)
        self.why = why
        s = ''
        if why is not None:
            s = ' (%s)' %(why,)
        if state != old:
            pstate = self.format.get(state,state)
            self.log.info('STATE change: {o} --> {n}{s}', o=old, n=pstate, s=s)

            if self.change_callback:
                self.change_callback(state, old, why)

    def get(self):
        return self.state

    def is_in(self,*args):
        if self.state in args:
            return True
        return False

    def not_in(self,*args):
        return not self.is_in(*args)

    def __str__(self):
        return str(self.state)



class ColorState(State):
    ''' A simple four state color inspired state variable; OFF RED YELLOW GREEN. combine()
        can be used to combine multiple ColorState objects into one common metric.
    ''' 
    
    def __init__(self,state=None,format=None,**kw):
        State.__init__(self,
                       state=state or 'OFF',
                       states=('OFF','YELLOW','RED','GREEN'),
                       format=format or { 'OFF': '\x1b[34mOFF\x1b[0m',
                                          'YELLOW': '\x1b[33mYELLOW\x1b[0m',
                                          'RED': '\x1b[31mRED\x1b[0m',
                                          'GREEN': '\x1b[32mGREEN\x1b[0m'},
                       **kw)

    def set_OFF(self,*a):
        self.set('OFF',*a)
    def set_YELLOW(self,*a):
        self.set('YELLOW',*a)
    def set_RED(self,*a):
        self.set('RED',*a)
    def set_GREEN(self,*a):
        self.set('GREEN',*a)

    def combine(self,*state):
        ''' Combine a list of states into self.state. If any is RED, then output
            will be RED. If all are OFF or GREEN, the result will be OFF or GREEN
            respectively. Otherwise the state will be YELLOW. '''
        off = [ s.state == 'OFF' for s in state ]
        reds = [ s.state == 'RED' for s in state ]
        green = [ s.state == 'GREEN' for s in state ]
        if any(reds):
            self.set('RED')
        elif all(green):
            self.set('GREEN')
        elif all(off):
            self.set('OFF')
        else:
            self.set('YELLOW')

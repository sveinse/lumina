#-*- python -*-

from .log import *



class State(object):
    ''' Class for keeping a state variable. States can be set using set(state, *args), and read
        with get(). It will log an entry when the state changes on set, and it can run a callback
        on changes.
    '''

    def __init__(self,state,system=None,change_callback=None,*args):
        self.state = state or 'init'
        self.system = system
        self.args = args[:]
        self.change_callback = change_callback


    def set(self,state,*args):
        (old, self.state) = (self.state, state)
        self.args = args[:]
        s = ''
        if len(args):
            s = ' (%s)' %(",".join(args))
        if state != old:
            log("STATE change: %s --> %s%s" %(old,state,s), system=self.system)

            if self.change_callback:
                self.change_callback(self.state, old, *args)


    def get(self):
        return self.state


    def is_in(self,*args):
        if self.state in args:
            return True
        return False

# -*-python-*-
import os,sys
import array
from ola.OlaClient import OlaClient
from twisted.python import log

from ..endpoint import Endpoint


class Led(Endpoint):
    universe = 0
    system = 'LED'
    name = 'LED'

    # --- Interfaces
    def configure(self):
        self.events = [ ]

        self.commands = {
            'led/state'   : lambda a : self.state,
            'led'         : lambda a : self.command(a.args[0],a.args[1],a.args[2],a.args[3]),
        }


    # --- Initialization
    def __init__(self,config):
        self.state = 'init'

    def setup(self):
        (old, self.state) = (self.state, 'active')
        log.msg("STATE change: '%s' --> '%s'" %(old,self.state), system=self.system)


    # --- Commands
    def command(self,r,g,b,w):
        self.dmx = OlaClient()
        data = array.array('B')
        data.append(int(r))
        data.append(int(g))
        data.append(int(b))
        data.append(int(w))
        self.dmx.SendDmx(self.universe, data, None)



# Main plugin object class
PLUGIN = Led

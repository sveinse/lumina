# -*-python-*-
import os,sys
import array
from endpoint import Endpoint
from ola.OlaClient import OlaClient
from twisted.python import log


class Led(Endpoint):
    universe = 0

    def get_actions(self):
        return {
            'led/state'   : lambda a : self.state,
            'led/off'     : lambda a : self.command(0,0,0,0),
            'led/white'   : lambda a : self.command(0,0,0,255),
            'led/blue'    : lambda a : self.command(0,0,255,0),
            'led/raw'     : lambda a : self.command(a.args[0],a.args[1],a.args[2],a.args[3]),
        }


    # --- Initialization
    def __init__(self):
        self.dmx = OlaClient()
        self.state = 'active'
        log.msg("STATE change: '%s'" %(self.state,), system='LED')


    def command(self,r,g,b,w):
        data = array.array('B')
        data.append(int(r))
        data.append(int(g))
        data.append(int(b))
        data.append(int(w))
        self.dmx.SendDmx(self.universe, data, None)


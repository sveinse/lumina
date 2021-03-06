# -*-python-*-
""" LED-strip control via DMX over Open Lighting Architecture plugin """
from __future__ import absolute_import, division, print_function

import array

from ola.OlaClient import OlaClient  # pylint: disable=E0401

from lumina.node import Node



class Led(Node):
    ''' LED dimmer control interface '''

    universe = 0

    CONFIG = {
        'universe': dict(default=0, help='DMX universe to use', type=int),
    }

    # --- Interfaces
    def configure(self):

        self.events = (
        )

        self.commands = {
            'set'       : lambda a: self.command(*a.args),
        }


    # --- Initialization
    def setup(self):

        self.universe = self.master.config.get('universe', name=self.name)
        self.status.set_GREEN()


    # --- Commands
    def command(self, *args):
        self.dmx = OlaClient()
        data = array.array('B')
        data.append(int(args[0]))
        data.append(int(args[1]))
        data.append(int(args[2]))
        data.append(int(args[3]))
        self.dmx.SendDmx(self.universe, data, None)



PLUGIN = Led

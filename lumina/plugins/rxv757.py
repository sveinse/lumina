# -*-python-*-
from __future__ import absolute_import

from lumina.node import Node



class Rxv757(Node):
    ''' Yamaha RX-V757 IR interface '''

    CONFIG = {
    }

    DEPENDS = ['lirc']

    # --- Interfaces
    def configure(self, master):

        self.events = [
        ]

        self.commands = {
            'on' :         lambda a: self.c('Yamaha_RXV757', 'KEY_POWER_ON'),
            'off' :        lambda a: self.c('Yamaha_RXV757', 'KEY_POWER_OFF'),
            'pure_direct': lambda a: self.c('Yamaha_RXV757', 'KEY_PURE_DIRECT'),
            'mute' :       lambda a: self.c('Yamaha_RXV757', 'KEY_MUTE'),
        }


    # --- Initialization
    def setup(self, master):
        Node.setup(self, master)

        self.lirc = master.get_plugin_by_name('lirc')
        self.status.set_GREEN()


    def c(self, name, key):
        return self.lirc.command('SEND_ONCE', name, key)



PLUGIN = Rxv757

# -*- python -*-
from event import Event as E


class Logic(object):

    alias = {
        # Command        -> Action function
        # Command        -> ( list of 'command' | Event() | alias_function )
        #                     Alias function called with one argument. Allows
        #                     getting the command's parameters passed into the
        #                     alias function. It must return list, string,
        #                     Event() or other alias function.

        'light/full'      : ( 'led/pwr/on', 'spot/on', 'led/white/on' ),
        'light/normal'    : ( 'led/pwr/on', 'spot/on', 'led/blue/normal' ),
        'light/weak'      : ( 'led/pwr/on', 'spot/dim{30}', 'led/blue/dim{15}' ),
        'light/pause'     : ( 'led/pwr/on', 'spot/off', 'led/white/dim{10}' ),
        'light/off'       : ( 'spot/off', 'led/off' ),
        'light/pwr/off'   : ( 'spot/off', 'led/pwr/off' ),

        'spot/on'         : ( 'td/on{100}', ),
        'spot/off'        : ( 'td/off{100}', ),
        'spot/dim'        : ( lambda a : ( E('td/dim',100,a.args[0]), ), ),

        #'light/roof/on'   : ( 'td/on{101}', ),
        #'light/roof/off'  : ( 'td/off{101}', ),
        #'light/roof/on'  : ( 'td/on{102}', ),
        #'light/roof/off' : ( 'td/off{102}', ),
        #'light/roof/on'  : ( 'td/on{103}', ),
        #'light/roof/off' : ( 'td/off{103}', ),
        #'light/roof/on'  : ( 'td/on{104}', ),
        #'light/roof/off' : ( 'td/off{104}', ),
        #'light/table/on'  : ( 'td/on{105}', ),
        #'light/table/off' : ( 'td/off{105}', ),

        'led/pwr/on'      : ( 'td/on{106}', ),
        'led/pwr/off'     : ( 'td/off{106}', ),
        'led/white/on'    : ( 'led{0,0,0,255}', ),
        'led/white/normal': ( 'led{0,0,0,100}', ),
        'led/white/dim'   : ( lambda a : ( E('led',0,0,0,a.args[0]), ), ),
        'led/blue/normal' : ( 'led{0,0,100,0}', ),
        'led/blue/dim'    : ( lambda a : ( E('led',0,0,a.args[0],0), ), ),
        'led/off'         : ( 'led{0,0,0,0}', ),

        'elec/on'         : ( 'oppo/on', 'hw50/on', 'avr/on' ),
        'elec/off'        : ( 'oppo/off', 'hw50/off', 'avr/off' ),

    }

    jobs = {
        # Event -> Action(s)

        # Oppo initialization
        'oppo/connected' : 'oppo/verbose',

        # Nexa fjernkontroll
        'remote/1/on'    : 'elec/on',
        'remote/1/off'   : 'elec/off',

        'remote/3/on'    : 'spot/dim{30}',
        'remote/3/off'   : 'spot/off',
        'remote/4/on'    : 'led/white/dim{10}',
        'remote/4/off'   : 'led/off',

        'remote/g/on'    : 'light/normal',
        'remote/g/off'   : 'light/off',

        'remote/5/on'    : 'led{0,0,0,255}',
        'remote/5/off'   : 'led{0,0,0,15}',
        'remote/6/on'    : 'led{0,0,100,0}',
        'remote/6/off'   : 'led{0,0,17,0}',
        'remote/7/on'    : 'led{143,0,0,0}',
        'remote/7/off'   : 'led{9,0,0,0}',
        'remote/8/on'    : 'led{122,0,29,0}',
        'remote/8/off'   : 'led{10,0,4,0}',

        # Veggbryter overst hjemmekino
        'wallsw1/on'     : 'light/normal',
        'wallsw1/off'    : 'light/off',

        # Veggbryter nederst kino
        'wallsw2/on'     : 'light/weak',
        'wallsw2/off'    : 'light/pwr/off',

        # Oppo regler
        'oppo/pause'     : 'light/pause',
        'oppo/play'      : 'light/off',
        'oppo/stop'      : 'light/weak',
    }


    def setup(self):
        pass

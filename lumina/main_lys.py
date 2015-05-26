import os,sys
from telldus import Telldus
from oppo import Oppo
from utils import Utils
from server import Server


#
# Mapping of incoming events to outgoing actions.
# Actions can be string, Action() objects, or tuples with strings or Action() objects
#
jobs = {
    # Event -> Action(s)

    # Global events
    'starting'       : None,
    'stopping'       : None,

    # Telldus connections
    'td/starting'    : None,
    'td/connected'   : None,
    'td/error'       : None,

    # Oppo connections
    'oppo/starting'  : None,
    'oppo/connected' : None,
    'oppo/error'     : None,

    # Nexa fjernkontroll
    'remote/g/on'    : ( 'kino/led/on', 'kino/lys/on' ),
    'remote/g/off'   : ( 'kino/lys/off' ),
    'remote/3/on'    :   'kino/tak-reol/dim{30}',
    'remote/3/off'   :   'kino/tak-reol/off',
    'remote/4/on'    :   'kino/lys/dim{30}',
    'remote/4/off'   : ( 'kino/tak/off', 'kino/bord/dim{30}' ),

    #'remote/1/on'   :   'oppo/play',
    'remote/1/off'   : ( 'kino/lys/off', 'oppo/off' ),

    # Veggbryter overst hjemmekino
    'wallsw1/on'     : ( 'kino/led/on', 'kino/lys/on' ),
    'wallsw1/off'    : ( 'kino/lys/off', ),

    # Veggbryter nederst kino
    'wallsw2/on'     :   'kino/lys/dim{30}',
    'wallsw2/off'    : ( 'kino/lys/off', 'kino/led/off' ),

    # Oppo regler
    'oppo/pause'     :   'kino/lys/dim{30}',
    'oppo/play'      :   'kino/lys/off',
    'oppo/stop'      :   'kino/lys/dim{60}',

    # Temperatur
    'temp/ute'       : None,
    'temp/kjeller'   : None,
    'temp/loftute'   : None,
    'temp/kino'      : None,
    'temp/fryseskap' : None,
}



# The modules to start
modules = [
    Utils(),
    #Server(19537),
    Telldus(),
    Oppo('/dev/ttyUSB0'),
]

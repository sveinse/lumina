#-*- python -*-
from __future__ import absolute_import

# pylint: disable=C0326,C0103

# Named functions commands
# ========================
alias = {
    # Command -> ( list of 'commands' )

    # Test and debug aliases
    'zero'   : tuple(),
    'one'    : ( 'test/1', ),
    'two'    : ( 'test/1', 'test/2' ),
    'fail'   : ( 'test/1', 'test/fail', 'test/2' ),
    'unknown': ( 'test/1', 'gone', 'test/2' ),

    # Original aliases
    'light/full'      : ( 'telldus/light/on', 'telldus/ledpwr/on', 'led/white/on' ),
    'light/normal'    : ( 'telldus/light/on', 'telldus/ledpwr/on', 'led/blue/normal' ),
    'light/weak'      : ( 'telldus/light/dim{30}', 'telldus/ledpwr/on', 'led/blue/dim{15}' ),
    'light/pause'     : ( 'telldus/light/off', 'telldus/ledpwr/on', 'led/white/dim{10}' ),
    'light/off'       : ( 'telldus/light/off', 'led/off' ),
    'light/pwr/off'   : ( 'telldus/light/off', 'telldus/ledpwr/off' ),

    'led/pwr/on'      : ( 'telldus/ledpwr/on', ),
    'led/pwr/off'     : ( 'telldus/ledpwr/off', ),
    'led/white/on'    : ( 'led{0,0,0,255}', ),
    'led/white/normal': ( 'led{0,0,0,100}', ),
    'led/white/dim'   : ( 'led{0,0,0,$1}', ),
    'led/blue/normal' : ( 'led{0,0,100,0}', ),
    'led/blue/dim'    : ( 'led{0,0,$1,0}', ),
    'led/off'         : ( 'led{0,0,0,0}', ),

    #'elec/on'         : ( 'oppo/on', 'hw50/on', 'avr/on' ),
    #'elec/off'        : ( 'oppo/off', 'hw50/off', 'avr/off' ),

}


# Event responses
# ===============
#   List of responses to received events
responses = {
    # Event -> Action

    # Test and debug responses
    'zero' : 'zero',
    'one' : 'one',
    'two' : 'two',
    'fail' : 'fail',
    'unknown' : 'unknown',
    'test/zero' : 'zero',
    'test/one' : 'one',
    'test/two' : 'two',
    'test/fail' : 'fail',
    'test/unknown' : 'unknown',

    # Oppo initialization
    #'oppo/connected' : 'oppo/verbose',

    # Nexa fjernkontroll
    #'telldus/remote/1/on'    : 'elec/on',
    #'telldus/remote/1/off'   : 'elec/off',

    'telldus/remote/3/on'    : 'telldus/light/dim{30}',
    'telldus/remote/3/off'   : 'telldus/light/off',
    'telldus/remote/4/on'    : 'led/white/dim{10}',
    'telldus/remote/4/off'   : 'led/off',

    'telldus/remote/g/on'    : 'light/normal',
    'telldus/remote/g/off'   : 'light/off',

    'telldus/remote/5/on'    : 'led{0,0,0,255}',
    'telldus/remote/5/off'   : 'led{0,0,0,15}',
    'telldus/remote/6/on'    : 'led{0,0,100,0}',
    'telldus/remote/6/off'   : 'led{0,0,17,0}',
    'telldus/remote/7/on'    : 'led{143,0,0,0}',
    'telldus/remote/7/off'   : 'led{9,0,0,0}',
    'telldus/remote/8/on'    : 'led{122,0,29,0}',
    'telldus/remote/8/off'   : 'led{10,0,4,0}',

    'telldus/remote/9/on'    : 'telldus/ledpwr/on',
    'telldus/remote/9/off'   : 'telldus/ledpwr/off',
    'telldus/remote/10/on'   : 'telldus/light/table/on',
    'telldus/remote/10/off'  : 'telldus/light/table/off',
    'telldus/remote/11/on'   : 'telldus/light/roof/on',
    'telldus/remote/11/off'  : 'telldus/light/roof/off',
    'telldus/remote/12/on'   : 'telldus/light/on',
    'telldus/remote/12/off'  : 'telldus/light/off',

    # Veggbryter overst hjemmekino
    'telldus/wallsw1/on'     : 'light/normal',
    'telldus/wallsw1/off'    : 'light/off',

    # Veggbryter nederst kino
    'telldus/wallsw2/on'     : 'telldus/light/wall/on',
    'telldus/wallsw2/off'    : 'light/pwr/off',

    # Oppo regler
    #'oppo/pause'     : 'light/pause',
    #'oppo/play'      : 'light/off',
    #'oppo/stop'      : 'light/weak',

    # Graphite regler
    #'temp/ute'       : 'graphite/send{huset.ute,$*}',
    #'temp/kjeller'   : 'graphite/send{huset.kjeller,$*}',
    #'temp/fryseskap' : 'graphite/send{huset.fryseskap,$*}',
    #'temp/kino/ute'  : 'graphite/send{huset.kino_ute,$*}',
    #'temp/kino/inne' : 'graphite/send{huset.kino_inne,$*}',

}


# List of Telldus equipment
# =========================
telldus_config = [

    # Telldus output devices -- must be synced with tellstick.conf to work
    # name must contain a {op} field
    dict(t='dimmer', id=100, house= 4785058, unit=1, name='light/{op}'),
    dict(t='dimmer', id=101, house=83621799, unit=1, name='light/roof/{op}'),
    dict(t='dimmer', id=102, model=86669189, unit=2, name='light/pj/{op}'),
    dict(t='dimmer', id=103, model=11630920, unit=2, name='light/sceen/{op}'),
    dict(t='dimmer', id=104, model=50026144, unit=2, name='light/wall/{op}'),
    dict(t='dimmer', id=105, model=27361582, unit=1, name='light/table/{op}'),
    dict(t='switch', id=106, model=12052346, unit=1, name='ledpwr/{op}'),

    # Telldus input switches. name must contain a {method} field, and either an unit
    # attribute or num_units.
    dict(t='in', house=14244686, group=1, unit=1,       name='remote/g/{method}'),
    dict(t='in', house=14244686, group=0, num_units=16, name='remote/{unit}/{method}'),
    dict(t='in', house=366702,   group=0, unit=1,       name='wallsw1/{method}' ),
    dict(t='in', house=392498,   group=0, unit=1,       name='wallsw2/{method}' ),

    # Temperature devices
    #dict(t='temp', id=11,  name='temp/ute' ),
    #dict(t='temp', id=12,  name='temp/kjeller' ),
    #dict(t='temp', id=247, name='temp/fryser' ),
    #dict(t='temp', id=135, name='temp/kino/ute' ),
    #dict(t='temp', id=151, name='temp/kino/inne' ),

]

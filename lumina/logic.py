# -*- python -*-
from core import JobFn


class Logic(object):
    jobs = {
        # Event -> Action(s)

        # Oppo initialization
        'oppo/connected' : 'oppo/verbose',

        # Nexa fjernkontroll
        'remote/1/on'    : ( 'oppo/on', 'hw50/on', 'avr/on' ),
        'remote/1/off'   : ( 'oppo/off', 'hw50/off', 'avr/off' ),

        'remote/3/on'    : ( 'lys/dim{30}' ),
        'remote/3/off'   : ( 'lys/off' ),
        'remote/4/on'    : ( 'led/raw{0,0,0,10}' ),
        'remote/4/off'   : ( 'led/off' ),

        'remote/g/on'    : ( 'led/pwr/on', 'lys/on', 'led/raw{0,0,100,0}' ),
        'remote/g/off'   : ( 'lys/off', 'led/off' ),

        'remote/5/on'    : ( 'led/raw{0,0,0,255}' ),
        'remote/5/off'   : ( 'led/raw{0,0,0,17}' ),
        'remote/6/on'    : ( 'led/raw{0,0,100,0}' ),
        'remote/6/off'   : ( 'led/raw{0,0,0,17}' ),
        'remote/7/on'    : ( 'led/raw{143,0,0,0}' ),
        'remote/7/off'   : ( 'led/raw{9,0,0,0}' ),
        'remote/8/on'    : ( 'led/raw{122,0,29,0}' ),
        'remote/8/off'   : ( 'led/raw{10,0,4,0}' ),

        # Veggbryter overst hjemmekino
        'wallsw1/on'     : ( 'led/pwr/on', 'lys/on', 'led/raw{0,0,100,0}' ),
        'wallsw1/off'    : ( 'lys/off', 'led/off' ),

        # Veggbryter nederst kino
        'wallsw2/on'     : ( 'lys/dim{60}', 'led/raw{0,0,0,30}' ),
        'wallsw2/off'    : ( 'lys/off', 'led/pwr/off' ),

        # Oppo regler
        'oppo/pause'     : ( 'lys/off', 'led/raw{0,0,0,10}' ),
        'oppo/play'      : ( 'lys/off', 'led/off' ),
        'oppo/stop'      : ( 'lys/dim{30}', 'led/raw{0,0,0,10}' ),

    }


    def setup(self):
        self.jobs.update( {
            'test': JobFn(self.gen),
            } )


    def gen(self):
        print 'GENERATOR START'
        yield 'delay{2}'
        status = yield 'hw50/status_power'
        print 'STATUS', status
        lamp = yield 'hw50/lamp_timer'
        print 'LAMP', lamp
        #yield 'stop'

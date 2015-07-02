from core import JobFn


class Logic(object):
    jobs = {
        # Event -> Action(s)

        # Oppo initialization
        'oppo/connected' : 'oppo/verbose',

        # Nexa fjernkontroll
        'remote/g/on'    : ( 'td/on{106}', 'kino/lys/on' ),
        'remote/g/off'   : ( 'kino/lys/off' ),
        'remote/3/on'    :   'kino/tak-reol/dim{30}',
        'remote/3/off'   :   'kino/tak-reol/off',
        'remote/4/on'    :   'kino/lys/dim{30}',
        'remote/4/off'   : ( 'kino/tak/off', 'kino/bord/dim{30}' ),

        #'remote/1/on'   :   'oppo/play',
        'remote/1/off'   : ( 'oppo/off', 'hw50/off' ),

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

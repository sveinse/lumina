import os,sys
from hw50 import Hw50
from utils import Utils
from core import JobFn


def gen():
    print 'GENERATOR START'
    yield 'delay{2}'
    status = yield 'hw50/status_power'
    print 'STATUS', status
    lamp = yield 'hw50/lamp_timer'
    print 'LAMP', lamp
    yield 'stop'


jobs = {
    #'starting' : ( 'delay{2}', 'hw50/close' ),
    #'stopping' : ( 'log{A}','delay{2}','log{B}' ),
    #'hw50/connected': ( 'delay{2}','hw50/status','delay{2}','hw50/status' ),
    'hw50/connected': JobFn(gen),
}


# The modules to start
modules = [
    Utils(),
    Hw50('/dev/ttyUSB0'),
]

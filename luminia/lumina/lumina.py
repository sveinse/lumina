import os,sys

import telldus
from twisted.internet import reactor
from twisted.python import log
from twisted.python.log import startLogging



def handle_telldus_error(reason):
    log.msg("TELLDUS ERROR:",reason)


def handle_telldus_event(result):
    cmd, args = result

    house=args['house']
    method=args['method']
    group=args['group']
    unit=args['unit']

    log.msg("    >>>> DEBUG:  house=%s  group=%s  unit=%s  method=%s " %(house,group,unit,method))

    def lightson():
        log.msg("Turning on all lights")
        telldus.turnOn(4)

    def lightsoff():
        log.msg("Turning off all lights")
        telldus.turnOff(4)

    def dimlights():
        log.msg("Dimming all")
        telldus.dim(4,30)

    def onlytable():
        log.msg("Dim table, roof off")
        telldus.turnOff(5)
        telldus.dim(1,30)

    def onoroff(method,onfn,offfn):
        if method == 'turnon':
            onfn()
        elif method == 'turnoff':
            offfn()

    if house == '14244686':
        ## Nexa fjernkontroll
        #
        # Control codes are group 0, unit 1-16, method turnon/turnoff
        # Global (at the bottom) is group 1, unit 1
        log.msg("Event from remote control: %s, %s, %s" %(group,unit,method))
        if group == '1' and unit == '1':
            onoroff(method, lightson, lightsoff)
        elif group == '0' and unit == '4':
            onoroff(method, dimlights, onlytable)

    elif house == '366702':
        ## Veggknapp overst kinorom
        #
        # group 0, unit 1, method turnon/turnoff
        log.msg("Event from upper wall switch: %s, %s, %s" %(group,unit,method))
        if group == '0' and unit == '1':
            onoroff(method, lightson, lightsoff)

    elif house == '392498':
        ## Veggknapp nederst kinorom
        #
        # group 1, unit 1, method turnon/turnoff
        log.msg("Event from lower wall switch: %s, %s, %s" %(group,unit,method))
        if group == '0' and unit == '1':
            onoroff(method, dimlights, onlytable)

    else:
        log.msg("Unknown event: %s" %(args))



def main():
    startLogging(sys.stdout)

    d = telldus.setupEvents()
    d.addCallback(handle_telldus_event)
    d.addErrback(handle_telldus_error)

    print 'Server PID: %s' %(os.getpid())
    reactor.run()

import os,sys

from telldus import Telldus
import web

from twisted.internet import reactor
from twisted.python import log
from twisted.python.log import startLogging


telldusRunning = False


def handle_telldus_ready(result,td):
    ''' Called when telldus is ready to receive commands '''

    global telldusRunning
    telldusRunning = True
    log.msg("TELLDUS READY:",result)


def handle_telldus_error(reason,td):
    ''' Handle telldus failures '''

    global telldusRunning
    telldusRunning = False
    log.msg("TELLDUS ERROR: FAILED TO START")


def handle_telldus_event(result,td):
    ''' Handle incoming event from Telldus devices controls '''

    cmd, args = result

    house=args['house']
    method=args['method']
    group=args['group']
    unit=args['unit']

    log.msg("    >>>> DEBUG:  house=%s  group=%s  unit=%s  method=%s " %(house,group,unit,method))

    def lightson():
        log.msg("Turning on all lights")
        td.turnOn(4)

    def lightsoff():
        log.msg("Turning off all lights")
        td.turnOff(4)

    def dimlights():
        log.msg("Dimming all")
        td.dim(4,30)

    def onlytable():
        log.msg("Dim table, roof off")
        td.turnOff(5)
        td.dim(1,30)

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



#
# ***  MAIN  ***
#
def main():
    ''' Lumina entry point '''

    startLogging(sys.stdout)

    # Start Telldus integration
    td = Telldus()
    td.setup()
    td.addCallbackReady(handle_telldus_ready,td)
    td.addCallbackError(handle_telldus_error,td)
    td.addCallbackEvent(handle_telldus_event,td)

    # Start WEB interface
    web.setup()

    # Start everything
    print 'Server PID: %s' %(os.getpid())
    reactor.run()

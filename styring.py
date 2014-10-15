#!/usr/bin/python

from lysstyring import td
import time
import traceback


logfile = None

def log(msg):
    if logfile:
        logfile.write("%s: %s\n" %(time.asctime(), msg))


def lightson():
    log("Turning on all lights")
    td.turnOn(4)


def lightsoff():
    log("Turning off all lights")
    td.turnOff(4)


def dimlights():
    log("Dimming all")
    td.dim(4,30)


def onlytable():
    log("Dim table, roof off")
    td.dim(1,30)
    td.turnOff(5)


def onoroff(method,onfn,offfn):
    if method == 'turnon':
        onfn()
    elif method == 'turnoff':
        offfn()


def keypress(data):
    house=data['house']
    method=data['method']
    group=data['group']
    unit=data['unit']

    #print "    >>>> DEBUG:  house=%s  group=%s  unit=%s  method=%s " %(house,group,unit,method)

    if house == '14244686':
        ## Nexa fjernkontroll
        #
        # Control codes are group 0, unit 1-16, method turnon/turnoff
        # Global (at the bottom) is group 1, unit 1
        log("Event from remote control: %s, %s, %s" %(group,unit,method))
        if group == '1' and unit == '1':
            onoroff(method, lightson, lightsoff)
        elif group == '0' and unit == '4':
            onoroff(method, dimlights, onlytable)

         
    elif house == '366702':
        ## Veggknapp overst kinorom
        #
        # group 0, unit 1, method turnon/turnoff
        log("Event from upper wall switch: %s, %s, %s" %(group,unit,method))
        if group == '0' and unit == '1':
            onoroff(method, lightson, lightsoff)

    elif house == '392498':
        ## Veggknapp nederst kinorom
        #
        # group 1, unit 1, method turnon/turnoff
        log("Event from lower wall switch: %s, %s, %s" %(group,unit,method))
        if group == '0' and unit == '1':
            onoroff(method, dimlights, onlytable)

    else:
        log("Unknown event: %s" %(data))



#---------------------------------------------------------------------

def parsedata(data):
    pl=data.split(';')
    payload = dict()
    for p in pl:
        if p:
            kd=p.split(':')
            payload[kd[0]]=kd[1]
    return payload


def rawevent(data, controllerId, callbackId):
    try:
        orig = data
        data = parsedata(orig)

        #print "    >>>> DEBUG: ",data

        # Check that we have all the members we need
        if not all([s in data for s in ['class','protocol','house','method','group','unit']]):
            # Missing fields
            return

        cls=data['class']
        protcol=data['protocol']

        if cls not in ['command',]:
            # Wrong class type
            return
        if protcol not in ['arctech',]:
            # Wrong protcol type
            return

        keypress(data)
    except:
        traceback.print_exc()
    

def main():

    cb = [ ]
    rawevent("",1,1)

    try:
	global logfile
	logfile = open('/var/log/lys.log', 'w+', 0)

        td.init(defaultMethods = td.TELLSTICK_TURNON | td.TELLSTICK_TURNOFF | td.TELLSTICK_DIM)

        cb.append(td.registerRawDeviceEvent(rawevent))

        log("Started service")

        while(1):
            time.sleep(10)

    except KeyboardInterrupt:
        log("Ctrl+C received, exiting")

    for i in cb:
        td.unregisterCallback(i)

    td.close()
    logfile.close()

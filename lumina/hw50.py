# -*-python-*-
import os,sys

from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet.serialport import SerialPort

class HW50Protocol(Protocol):
     def dataReceived(self, data):
        print "HW50: (%s)'%s'" %(len(data),data)

def setup():
    ser = SerialPort(HW50Protocol(), '/dev/ttyUSB0', reactor, baudrate=115200)

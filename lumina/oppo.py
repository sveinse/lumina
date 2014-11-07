# -*-python-*-
import os,sys

from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet.serialport import SerialPort

class OppoProtocol(Protocol):
     def dataReceived(self, data):
        print "OPPO: (%s)'%s'" %(len(data),data)

def setup():
    ser = SerialPort(OppoProtocol(), '/dev/ttyUSB1', reactor, baudrate=115200)

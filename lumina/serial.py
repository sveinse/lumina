# -*- python -*-
from __future__ import absolute_import

from twisted.internet import reactor
from twisted.internet.serialport import SerialPort
from twisted.python.failure import Failure
from serial.serialutil import SerialException

from lumina.reconnector import Reconnector


class ReconnectingSerialPort(Reconnector):

    def __init__(self, protocol, port, *args, **kwargs):
        self.protocol = protocol
        self.port = port
        self.args = args
        self.kwargs = kwargs
        self.sp = None


    def connect(self):
        try:
            self.sp = SerialPort(self.protocol, self.port, reactor,
                                 *self.args, **self.kwargs)
            self.resetDelay()
        except SerialException as e:
            self.connectionFailed(Failure())


    def connectionLost(self, reason):
        self.sp = None
        Reconnector.connectionLost(self, reason)


    def connectionFailed(self, reason):
        self.sp = None
        Reconnector.connectionFailed(self, reason)


    def loseConnection(self, *args, **kwargs):
        Reconnector.stopTrying(self)
        if self.sp:
            self.sp.loseConnection(*args, **kwargs)

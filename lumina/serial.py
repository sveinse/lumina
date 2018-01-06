# -*- python -*-
""" Serial port functionality """
from __future__ import absolute_import

from twisted.internet.serialport import SerialPort
from twisted.python.failure import Failure
from serial.serialutil import SerialException

from lumina.reconnector import Reconnector


class ReconnectingSerialPort(Reconnector):
    """ A class for serial port connection that will retry the connection
        if the connection fails
    """

    def __init__(self, reactor, protocol, port, *args, **kwargs):
        Reconnector.__init__(self, reactor)
        self.protocol = protocol
        self.port = port
        self.args = args
        self.kwargs = kwargs
        self.serialport = None


    def connect(self):
        try:
            self.serialport = SerialPort(self.protocol, self.port, self.reactor,
                                         *self.args, **self.kwargs)
            self.resetDelay()
        except SerialException:
            self.connectionFailed(Failure())


    def connectionLost(self, reason):
        self.serialport = None
        self.retry()


    def connectionFailed(self, reason):
        self.serialport = None
        self.retry()


    def loseConnection(self, *args, **kwargs):
        ''' Lose connection to the serial port '''
        self.stopTrying()
        if self.serialport:
            self.serialport.loseConnection(*args, **kwargs)

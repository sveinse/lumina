# -*- python -*-

class LuminaException(Exception):
    ''' Base exception class for Lumina '''
    pass

class CommandException(LuminaException):
    pass
class NotConnectedException(CommandException):
    pass
class CommandFailedException(CommandException):
    pass
class TimeoutException(CommandException):
    pass

class ClientException(LuminaException):
    ''' Unknown error received from client '''
    pass

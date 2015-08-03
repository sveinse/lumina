# -*- python -*-

class LuminaException(Exception):
    ''' Base exception class for Lumina '''

class CommandException(LuminaException):
    ''' Command execution exception base class '''
class NotConnectedException(CommandException):
    pass
class CommandFailedException(CommandException):
    pass
class TimeoutException(CommandException):
    pass

class CommandRunException(LuminaException):
    ''' Error running a command '''
class UnknownCommandException(CommandRunException):
    pass


class ClientException(LuminaException):
    ''' Unknown error received from client '''

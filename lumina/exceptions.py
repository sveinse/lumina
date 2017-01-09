# -*- python -*-
from __future__ import absolute_import


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
class CommandParseException(CommandException):
    pass
class CommandRunException(CommandException):
    ''' Error running a command '''
class UnknownCommandException(CommandException):
    pass


class ClientException(LuminaException):
    ''' Unknown error received from client '''


class ConfigException(LuminaException):
    ''' Errors related to configuration '''


class NoConnectionException(LuminaException):
    ''' Connection errors '''
class LostConnectionException(LuminaException):
    ''' Lost connection error '''

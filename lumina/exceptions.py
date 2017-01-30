# -*- python -*-
from __future__ import absolute_import


class LuminaException(Exception):
    ''' Base exception class for Lumina '''


class TimeoutException(LuminaException):
    ''' Operation has timed out '''

class CommandParseException(LuminaException):
    ''' Problems parsing the command '''

class CommandRunException(LuminaException):
    ''' Error running a command '''

class UnknownCommandException(LuminaException):
    ''' Unknown command '''

class NodeException(LuminaException):
    ''' Error received from a node '''

class NodeConfigException(LuminaException):
    ''' Error from configuring a node '''

class ConfigException(LuminaException):
    ''' Errors related to configuration '''

class NoConnectionException(LuminaException):
    ''' Connection errors '''

#FIXME: Old exception from the old plugins
#class CommandFailedException(LuminaException):
#    pass

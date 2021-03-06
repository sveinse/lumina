# -*- python -*-
""" Lumina exceptions """
from __future__ import absolute_import, division, print_function


class LuminaException(Exception):
    ''' Base exception class for Lumina '''


class TimeoutException(LuminaException):
    ''' Operation has timed out '''

class CommandParseException(LuminaException):
    ''' Problems parsing the command '''

class CommandRunException(LuminaException):
    ''' Error running a command '''

class UnknownMessageException(LuminaException):
    ''' Unknown message exception '''

class UnknownCommandException(LuminaException):
    ''' Unknown command '''

class NodeException(LuminaException):
    ''' Error received from a node '''

class NodeConfigException(LuminaException):
    ''' Error from configuring a node '''

class NodeRegistrationException(LuminaException):
    ''' Error registering a node '''

class ConfigException(LuminaException):
    ''' Errors related to configuration '''

class NoConnectionException(LuminaException):
    ''' Connection errors '''

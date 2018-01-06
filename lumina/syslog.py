#-*- python -*-
""" Syslog log observer """
from __future__ import absolute_import, division, print_function

import syslog

from zope.interface import implementer
from twisted.logger import ILogObserver
from twisted.logger import LogLevel
from twisted.logger import formatEvent


# These defaults come from the Python syslog docs.
DEFAULT_OPTIONS = 0
DEFAULT_FACILITY = syslog.LOG_USER

# Map the twisted LogLevels up against the syslog values
LOGLEVEL_MAP = {
    LogLevel.debug: syslog.LOG_DEBUG,
    LogLevel.info: syslog.LOG_INFO,
    LogLevel.warn: syslog.LOG_WARNING,
    LogLevel.error: syslog.LOG_ERR,
    LogLevel.critical: syslog.LOG_CRIT,
}


@implementer(ILogObserver)
class SyslogObserver(object):
    """
    A log observer for logging to syslog.
    """

    openlog = syslog.openlog
    syslog = syslog.syslog


    def __init__(self, prefix, options=DEFAULT_OPTIONS,
                 facility=DEFAULT_FACILITY):
        """
        """
        self.openlog(prefix, options, facility)


    def __call__(self, event):
        """
        Write event to syslog.
        """

        # Figure out what the message-text is.
        eventText = formatEvent(event)
        if eventText is None:
            return

        # Figure out what syslog parameters we might need to use.
        level = event.get("log_level", None)
        if level is None:
            if 'log_failure' in event:
                level = LogLevel.critical
            else:
                level = LogLevel.info
        priority = LOGLEVEL_MAP[level]
        facility = int(event.get('log_facility', DEFAULT_FACILITY))

        # Break the message up into lines and send them.
        lines = eventText.split('\n')
        while lines[-1:] == ['']:
            lines.pop()

        firstLine = True
        for line in lines:
            if firstLine:
                firstLine = False
            else:
                line = '        ' + line
            self.syslog(priority | facility,
                        '[%s] %s' % (event.get('log_system', '-'), line))

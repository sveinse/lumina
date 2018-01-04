#-*- python -*-
""" 
Log function. Import 'Logger' and make an instance of it to do proper
logging.
"""
from __future__ import absolute_import

import sys

from zope.interface import implementer
from twisted.logger import Logger
from twisted.logger import ILogObserver
from twisted.logger import formatTime
from twisted.logger import formatEvent
from twisted.logger import globalLogBeginner
from twisted.logger import globalLogPublisher
from twisted.logger import FileLogObserver
from twisted.logger import FilteringLogObserver
from twisted.logger import LogLevelFilterPredicate
from twisted.logger import LogLevel
from twisted.logger import ILogFilterPredicate
from twisted.logger import PredicateResult
from twisted.python.compat import unicode

# Some architectures does not support syslog
SYSLOG_IMPORTED = True
try:
    from lumina.syslog import SyslogObserver
except ImportError:
    SYSLOG_IMPORTED = False

__all__ = ["start", "Logger", "LogLevel"]



# Mod of twisted.logger.formatEventAsClassicLogText()
def formatLuminaLogText(event, formatTime=formatTime):
    """ Format an event as a line of human-readable text. """

    eventText = formatEvent(event)
    if not eventText:
        return None

    eventText = eventText.replace(u"\n", u"\n\t")
    timeStamp = formatTime(event.get("log_time", None))
    system = event.get("log_system", None)

    level = event.get("log_level", None)
    if level is None:
        levelName = u"-"
    else:
        levelName = level.name

    return u"{timeStamp} {level:<8} [{system}]  {event}\n".format(
        timeStamp=timeStamp,
        level=levelName,
        system=system,
        event=eventText,
    )


# List of special log variables
log_specials = {
    'rawin'  : lambda d: "RAW  >>>  ({l})'{d}'".format(l=len(d), d=d),
    'rawout' : lambda d: "RAW  <<<  ({l})'{d}'".format(l=len(d), d=d),
    'datain' : lambda d: "  >>>  {d}".format(d=d),
    'dataout': lambda d: "  <<<  {d}".format(d=d),
    'cmdin'  : lambda d: "  -->  {d}".format(d=d),
    'cmdout' : lambda d: "  <--  {d}".format(d=d),
    'cmdok'  : lambda d: "   OK  {d}".format(d=d),
    'cmderr' : lambda d: "  ERR  {d}".format(d=d),
}


@implementer(ILogObserver)
class LuminaLogFormatter(object):
    ''' Logging observer for Lumina '''

    def __call__(self, event):
        ''' Main dispatcher for log-events '''


        # STEP 1) log_system must always be valid. Lumina use it to pass
        #         on log_namespace mostly. Both the SyslogObserver and
        #         formatLuminaLogText depend on it being set.
        system = event.get("log_system", None)
        if system is None:
            system = event.get("log_namespace", u"-")
        else:
            try:
                system = unicode(system)
            except Exception:
                system = u"UNFORMATTABLE"
        event['log_system'] = system


        # STEP 2) Inject the special lumina logging types

        # It works by seraching if any of the special variables are
        # present in the event. If it is, the given print function is
        # run and the variable is stored in _name. This can then be
        # accessed from the logged text by using {_name}.

        #fmt = event['log_format']
        for (var, fn) in log_specials.items():
            if var in event:
                event['_' + var] = fn(event[var])

                # If the special var is not present in the
                # format string, add it to the end
                #dvar = '{_' + var + '}'
                #if dvar not in fmt:
                #    fmt += dvar
        #event['log_format'] = fmt


        # STEP 3) If a log_failure is encountered, fetch the traceback
        #         and modify log_format to contain the original message +
        #         the traceback.
        if "log_failure" in event:
            eventText = formatEvent(event)
            try:
                traceback = event["log_failure"].getTraceback()
            except:
                traceback = u"(UNABLE TO OBTAIN TRACEBACK FROM EVENT)\n"
            event['log_text'] = u"\n".join((eventText, traceback))
            event['log_format'] = '{log_text}'



@implementer(ILogFilterPredicate)
class LuminaFilterPredicate(object):
    ''' Log filter engine '''

    # Lazy shortcuts
    yes = PredicateResult.yes
    no = PredicateResult.no
    maybe = PredicateResult.maybe


    def __init__(self, minimumLoglevel=LogLevel.info):
        ''' Setup the filter engine. 'minimumLoglevel' sets the global
            overall minimum log-level
        '''
        self.minLoglevel = minimumLoglevel


    def __call__(self, event):
        ''' Run the filtertest on the event '''

        # FIXME: This should be far more configurable

        # Handle message without log_level
        if not event.get('log_level', None):
            return self.yes

        log_level = event.get('log_level')

        # Important messages goes through always
        if log_level >= LogLevel.error:
            return self.yes

        namespace = event.get('log_namespace', '')

        # Filter out all RAW packages
        if 'rawin' in event or 'rawout' in event:
            return self.no

        # Ignore data in and data out messages for node connection on server
        if ':' in namespace and ('datain' in event or 'dataout' in event or 'cmdok' in event):
            return self.no

        # Telldus input is very noisy
        if namespace == 'telldus/in' and ('datain' in event):
            return self.no

        # Ignore anything less than our min Level?
        if log_level < self.minLoglevel:
            return self.no

        return self.maybe



def start(syslog=False, logfile=None, syslog_prefix='lumina', redirect_stdio=False,
          loglevel=None):
    ''' Start the custom logger '''

    # System defaults from twisted.logger._global.py:
    #   globalLogPublisher = LogPublisher()
    #   globalLogBeginner = LogBeginner(globalLogPublisher, sys.stderr, sys, warnings)

    if logfile is None:
        logfile = sys.stdout

    if loglevel is None:
        loglevel = LogLevel.info

    # Lumina log observers
    if syslog and SYSLOG_IMPORTED:
        out_observer = SyslogObserver(prefix=syslog_prefix)
    else:
        out_observer = FileLogObserver(sys.stdout, formatLuminaLogText)

    #level_filter = LogLevelFilterPredicate(defaultLogLevel=loglevel)
    #level_filter.setLogLevelForNamespace('server', LogLevel.warn)

    observers = (
        LuminaLogFormatter(),
        FilteringLogObserver(
            out_observer,
            [ #level_filter,
                LuminaFilterPredicate(minimumLoglevel=loglevel),
            ]
        ),
    )

    # This logger will take over the system (the default LogPublisher). It will
    # iterate over any messages that has already been logged prior to
    # this registration. However, any errors in the observers will be silently
    # ignored because the observers are no longer run through the
    # LogPublisher()
    globalLogBeginner.beginLoggingTo(observers,
                                     redirectStandardIO=redirect_stdio)

    # Alternatively, register the observers using the default (global)
    # LogPublisher (found in twisted.logger._observer.py) . The upside with
    # this approach is that any errors in the observes will be catched and
    # printed. The downside is that it is not possible to prevent redirection
    # of stdio and it will not replay pre-logger entries prior to installation.
    # It will also print failure messages >=critical to sys.stderr because
    # _temporaryObserver is still installed. (see self._temporaryObserver in
    # LogBeginner)
    #for obs in observers:
    #    globalLogPublisher.addObserver(obs)

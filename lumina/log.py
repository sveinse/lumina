#-*- python -*-
import sys
from zope.interface import implementer
from twisted.logger import Logger
from twisted.logger import ILogObserver
from twisted.logger import formatTime
from twisted.logger import formatEvent, formatEventAsClassicLogText
from twisted.logger import globalLogBeginner, globalLogPublisher, LegacyLogObserverWrapper
from twisted.python.syslog import SyslogObserver
from twisted.python.compat import ioType, unicode


__all__ = [ "startLogging", "Logger" ]


class LuminaSyslogObserver(SyslogObserver):
    def __call__(self,event):
        return self.emit(event)



@implementer(ILogObserver)
class LuminaLogObserver(object):
    
    def __init__(self, syslog=None, syslog_prefix=''):

        self.syslog = None
        self.stdout = sys.stdout

        if ioType(self.stdout) is not unicode:
            self._encoding = "utf-8"
        else:
            self._encoding = None
        
        if syslog:
            self.syslog = LegacyLogObserverWrapper(LuminaSyslogObserver(prefix=syslog_prefix))

    
    def __call__(self,event):

        # Check if the message should be printed or suppressed
        ok = self.filterLogText(event)
        if not ok:
            return

        # Add the Lumina specific log items and generate the text for output
        self.addCustomLogText(event)
        self.formatLogText(event)

        if self.syslog is None:

            text = "{l_timestamp} {l_level:<6} {log_namespace:<24} [{system}]  {message}\n".format(**event)
            #text = formatEventAsClassicLogText(event)#

            #if not text:
            #    return

            if self._encoding is not None:
                text = text.encode(self._encoding)

            self.stdout.write(text)
            self.stdout.flush()
                
        else:
            self.syslog(event)



    def formatLogText(self, event):
        
        # == TIMESTAMP
        event['l_timestamp'] = formatTime(event.get("log_time", None))

        # == LEVEL
        level = event.get("log_level", None)
        if level is None:
            levelName = u"-"
        else:
            levelName = level.name
        event['l_level'] = levelName

        # == SYSTEM

        # To ensure using system if it is present and log_system is not
        if 'log_system' not in event:
            if 'system' in event:
                event['log_system'] = event['system']
            elif 'log_namespace' in event:
                event['log_system'] = event['log_namespace']

        system = event.get("log_system", None)
        if system is None:
            system = u"{namespace}#{level}".format(
                namespace=event.get("log_namespace", u"-"),
                level=levelName,
            )
        else:
            try:
                system = unicode(system)
            except Exception:
                system = u"UNFORMATTABLE"
        event['system'] = system

        # == MESSAGE
        eventText = formatEvent(event)

        if "log_failure" in event:
            try:
                traceback = event["log_failure"].getTraceback()
            except:
                traceback = u"(UNABLE TO OBTAIN TRACEBACK FROM EVENT)\n"
            eventText = u"\n".join((eventText, traceback))

        if not eventText:
            eventText = ''

        eventText = eventText.replace(u"\n", u"\n\t")
        event['message'] = eventText



    def addCustomLogText(self, event):
        
        fmt = event['log_format']
        
        specials = (
            ('rawin',   lambda d: "RAW  >>>  ({l})'{d}'".format(l=len(d),d=d) ),
            ('rawout',  lambda d: "RAW  <<<  ({l})'{d}'".format(l=len(d),d=d) ),
            ('datain',  lambda d: "  >>>  {d}".format(d=d) ),
            ('dataout', lambda d: "  <<<  {d}".format(d=d) ),
            ('cmdin',   lambda d: "  -->  {d}".format(d=d) ),
            ('cmdout',  lambda d: "  <--  {d}".format(d=d) ),
            ('cmdok',   lambda d: "   OK  {d}".format(d=d) ),
            ('cmderr',  lambda d: "  ERR  {d}".format(d=d) ),
        )

        # Replace the specials
        for (var,fn) in specials:
            if var in event:
                event['_' + var] = fn(event[var])
                dvar = '{_' + var + '}'
                if dvar not in fmt:
                    fmt += dvar
        
        # == Generate the log message
        event['log_format'] = fmt
        
    
    
    def filterLogText(self,event):

        # FIXME: Implement a confiugurable filter engine
        
        namespace = event.get('log_namespace','')
        
        # Filter out all RAW packages
        if 'rawin' in event or 'rawout' in event:
            return False

        # Ignore data in and data out messages for node connection on server
        if ':' in namespace and ('datain' in event or 'dataout' in event or 'cmdok' in event):
            return False
            
        # Telldus input is very noisy
        if namespace == 'telldus/in' and ('datain' in event):
            return False

        return True



def startLogging(syslog,syslog_prefix):
    
        # This logger will take over the system and will not give any feedback if the logger is failing
        globalLogBeginner.beginLoggingTo([LuminaLogObserver(syslog=syslog,syslog_prefix=syslog_prefix)])

        # This logger will allow failures on the logging system to be seen
        #globalLogPublisher.addObserver(LuminaLogObserver(syslog=syslog,syslog_prefix=syslog_prefix) )

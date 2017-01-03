#-*- python -*-
from __future__ import absolute_import

import traceback
from twisted.python import log as tlog


# FIXME: Change to config option
LOG_RAW=False
LOG_DATA=True
LOG_CMD=True


#== Basic log methods
def log(*args,**kw):
    tlog.msg(*args,**kw)

def err(*args,**kw):
    tlog.msg('ERROR:',*args,**kw)

def warn(*args,**kw):
    tlog.msg('WARNING:',*args,**kw)

def exclog(*args,**kw):
    tlog.msg('ERROR:',*args,**kw)
    tlog.msg(traceback.format_exc(),**kw)


#== Special or conditional log methods
#def lograw(text,data,**kw):
#    if LOG_RAW:
#        tlog.msg(text + "(%s)'%s'" %(len(data),data), **kw)
def lograwout(data,**kw):
    if LOG_RAW:
        tlog.msg("RAW  <<<  (%s)'%s'" %(len(data),data), **kw)
def lograwin(data,**kw):
    if LOG_RAW:
        tlog.msg("RAW  >>>  (%s)'%s'" %(len(data),data), **kw)

def logdataout(data,**kw):
    if LOG_DATA:
        tlog.msg("   <--  %s" %(data,), **kw)
def logdatain(data,**kw):
    if LOG_DATA:
        tlog.msg("   -->  %s" %(data,), **kw)
#def logtimeout(data,**kw):
#    tlog.msg("   -->  TIMEOUT %s" %(data,), **kw)

#def logevent(event,**kw):
#    tlog.msg("~~~  %s" %(event), **kw)

def logcmdok(event,**kw):
    if LOG_CMD:
        tlog.msg("    OK  %s" %(event), **kw)
def logcmderr(event,**kw):
    if LOG_CMD:
        tlog.msg("   ERR  %s" %(event), **kw)

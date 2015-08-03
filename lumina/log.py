#-*- python -*-

from twisted.python.log import msg,err

LOG_RAW=False
LOG_DATA=True

def log(*args,**kw):
    msg(*args,**kw)

def lograw(text,data,**kw):
    if LOG_RAW:
        msg(text + "(%s)'%s'" %(len(data),data), **kw)
def lograwout(data,**kw):
    if LOG_RAW:
        msg("RAW  <<<  (%s)'%s'" %(len(data),data), **kw)
def lograwin(data,**kw):
    if LOG_RAW:
        msg("RAW  >>>  (%s)'%s'" %(len(data),data), **kw)

def logdataout(data,**kw):
    if LOG_DATA:
        msg("   <--  %s" %(data,), **kw)
def logdatain(data,**kw):
    if LOG_DATA:
        msg("   -->  %s" %(data,), **kw)
def logtimeout(data,**kw):
    msg("   -->  TIMEOUT %s" %(data,), **kw)

def logevent(event,**kw):
    msg("~~~  %s" %(event), **kw)

# -*-python-*-
import sys,os
sys.path.append(os.path.join(os.path.dirname(__file__),'..'))

from ep_telldus import *


if __name__ == "__main__":
    from twisted.python.log import startLogging
    startLogging(sys.stdout)

    def error(reason,td):
        log.msg("ERROR",reason)
        reactor.stop()

    def ready(result,td):
        log.msg("READY",result)
        d = td.turnOn(1)
        d = td.turnOn(2)
        d = td.turnOn(3)

    def event(result,td):
        log.msg("EVENT",result)

    td = Telldus()
    d = td.setup()
    td.addCallbackReady(ready,td)
    td.addCallbackError(error,td)
    td.addCallbackEvent(event,td)
    d = td.turnOn(1)
    d = td.turnOn(2)
    d = td.turnOn(3)

    reactor.run()

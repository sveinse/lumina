import os,sys,atexit

from core import Core
from telldus import Telldus
from oppo import Oppo
import web

from twisted.internet import reactor
from twisted.python import log, syslog



#
# Mapping of incoming events to outgoing actions.
# Actions can be string, Action() objects, or tuples with strings or Action() objects
#
rules = {
    # Event -> Action(s)

    # Telldus connections
    'td/starting' : None,
    'td/connected' : None,
    'td/error': None,

    # Oppo connections
    'oppo/starting': None,
    'oppo/connected': None,
    'oppo/error': None,

    # Nexa fjernkontroll
    'td/remote/g/on' :   'td/lights/on',
    'td/remote/g/off':   'td/lights/off',
    'td/remote/4/on' :   'td/lights/dim{30}',
    'td/remote/4/off': ( 'td/roof/off', 'td/table/dim{30}' ),

    #'td/remote/1/on' :   'oppo/play',
    'td/remote/1/off': ( 'td/lights/off', 'oppo/off' ),

    # Veggbryter overst hjemmekino
    'td/wallsw1/on'  :   'td/lights/on',
    'td/wallsw1/off' :   'td/lights/off',

    # Veggbryter nederst kino
    'td/wallsw2/on'  :   'td/lights/dim{30}',
    'td/wallsw2/off' : ( 'td/roof/off', 'td/table/dim{30}' ),

    # Oppo regler
    'oppo/pause'     :   'td/lights/dim{30}',
    'oppo/play'      :   'td/lights/off',
    'oppo/stop'      :   'td/lights/on',
}



#
# ***  BECOME DAEMON  ***
#
def daemonize(pidfile):

    def delpid():
        try:
            os.remove(pidfile)
        except OSError:
            pass

    try:
        with file(pidfile,'r') as pf:
            pid = int(pf.read().strip())
    except IOError:
        pid = None
    if pid:
        sys.stderr.write("%s: pidfile '%s' exists. Refusing to start daemon\n" %(sys.argv[0],pidfile))
        sys.exit(1)

    # Fork #1
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    os.chdir("/")
    os.setsid()
    os.umask(0)

    # Fork #2
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    # Redirect stdout
    sys.stdout.flush()
    sys.stderr.flush()
    si = file('/dev/null', 'r')
    so = file('/dev/null', 'a+')
    se = file('/dev/null', 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    # Write pidfile
    atexit.register(delpid)
    file(pidfile,'w+').write(str(os.getpid()) + '\n')



#
# ***  MAIN  ***
#
def lumina(use_syslog=False):
    ''' Lumina entry point '''

    if use_syslog:
        syslog.startLogging(prefix='Lumina')
    else:
        log.startLogging(sys.stdout)

    # Prepare the event, actions and rules handling
    core = Core()
    core.addrules(rules)

    # Start Telldus integration
    td = Telldus()
    td.add_eventcallback(core.handle_event)
    core.addactions(td.get_actions())
    td.setup()

    # Start Oppo integration
    oppo = Oppo('/dev/ttyUSB0')
    oppo.add_eventcallback(core.handle_event)
    core.addactions(oppo.get_actions())
    oppo.setup()

    # Start WEB interface
    #web.setup()

    # Start everything
    print 'Server PID: %s' %(os.getpid())
    reactor.run()



#
# ***  HW-50 MAIN  ***
#
def hw50(use_syslog=False):
    ''' Luminia HW50 entry point '''

    if use_syslog:
        syslog.startLogging(prefix='Lumina')
    else:
        log.startLogging(sys.stdout)

    # Start everything
    print 'Server PID: %s' %(os.getpid())
    reactor.run()

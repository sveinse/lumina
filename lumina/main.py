import os,sys,atexit

from twisted.internet import reactor
from twisted.python import log, syslog



#
# Mapping of incoming events to outgoing actions.
# Actions can be string, Action() objects, or tuples with strings or Action() objects
#
jobs = {
    # Event -> Action(s)

    # Telldus connections
    'td/starting'    : None,
    'td/connected'   : None,
    'td/error'       : None,

    # Oppo connections
    'oppo/starting'  : None,
    'oppo/connected' : None,
    'oppo/error'     : None,

    # Nexa fjernkontroll
    'remote/g/on'    :   'kino/lys/on',
    'remote/g/off'   :   'kino/lys/off',
    'remote/4/on'    :   'kino/lys/dim{30}',
    'remote/4/off'   : ( 'kino/tak/off', 'kino/bord/dim{30}' ),

    #'remote/1/on'   :   'oppo/play',
    'remote/1/off'   : ( 'kino/lys/off', 'oppo/off' ),

    # Veggbryter overst hjemmekino
    'wallsw1/on'     :   'kino/lys/on',
    'wallsw1/off'    :   'kino/lys/off',

    # Veggbryter nederst kino
    'wallsw2/on'     :   'kino/lys/dim{30}',
    'wallsw2/off'    : ( 'kino/tak/off', 'kino/bord/dim{30}' ),

    # Oppo regler
    'oppo/pause'     :   'kino/lys/dim{30}',
    'oppo/play'      :   'kino/lys/off',
    'oppo/stop'      :   'kino/lys/dim{60}',

    # Temperatur
    'temp/ute'       : None,
    'temp/kjeller'   : None,
    'temp/loftute'   : None,
    'temp/kino'      : None,
    'temp/fryseskap' : None,
}



#
# ***  Become DAEMON  ***
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
def lys(use_syslog=False):
    ''' Lumina Lys entry point '''

    # Imports
    from core import Core
    from telldus import Telldus
    from oppo import Oppo
    import web

    if use_syslog:
        syslog.startLogging(prefix='Lumina')
    else:
        log.startLogging(sys.stdout)

    # Main server handler
    core = Core()

    # Start Telldus integration
    td = Telldus()
    td.add_eventcallback(core.handle_event)
    core.add_events(td.get_events())
    core.add_actions(td.get_actions())

    # Start Oppo integration
    oppo = Oppo('/dev/ttyUSB0')
    oppo.add_eventcallback(core.handle_event)
    core.add_events(oppo.get_events())
    core.add_actions(oppo.get_actions())

    # Register all the jobs
    core.add_jobs(jobs)

    # Setup the services
    td.setup()
    oppo.setup()
    #web.setup()

    # Start everything
    print 'Server PID: %s' %(os.getpid())
    reactor.run()



#
# ***  HW-50 MAIN  ***
#
def hw50(use_syslog=False):
    ''' Luminia HW50 entry point '''

    # Imports
    #from core import Core
    #from telldus import Telldus
    #from oppo import Oppo
    #import web

    if use_syslog:
        syslog.startLogging(prefix='Lumina')
    else:
        log.startLogging(sys.stdout)

    # Start everything
    print 'Server PID: %s' %(os.getpid())
    reactor.run()

import os,sys,atexit
from twisted.internet import reactor
from twisted.python import log


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
# ***  Helper ***
#
def register(parent,obj):
    ''' Register endpoint handler '''
    obj.add_eventcallback(parent.handle_event)
    parent.add_events(obj.get_events())
    parent.add_actions(obj.get_actions())
    obj.setup()



#
# ***  CONTROLLER  ***
#
def controller():

    from controller import Controller
    from utils import Utils
    from logic import Logic

    # Main controller
    controller = Controller(port=8081)
    controller.setup()

    # Logic/rules handler
    logic = Logic()
    logic.setup()
    controller.add_jobs(logic.jobs)

    # System Functions
    register(controller, Utils())



#
# ***  CLIENT LYS  ***
#
def client_lys():

    from client import Client
    from telldus import Telldus
    from oppo import Oppo
    from demo import Demo

    # Main controller
    cli = Client(host='localhost',port=8081,name='lys')
    cli.setup()

    # System Functions
    register(cli, Telldus())
    register(cli, Oppo('/dev/ttyUSB0'))



#
# ***  CLIENT HW50  ***
#
def client_hw50():

    from client import Client
    from hw50 import Hw50

    # Main controller
    cli = Client(host='lys',port=8081,name='hw50')
    cli.setup()

    # System Functions
    register(cli, Hw50('/dev/ttyUSB0'))



#
# ***  MAIN  ***
#
#def main(modules,jobs,use_syslog=False):
#    ''' Main Entry poin '''
#
#    if use_syslog:
#        syslog.startLogging(prefix='Lumina')
#    else:
#        log.startLogging(sys.stdout)
#
#    # Main server handler
#    core = Core()
#
#    # Register all modules
#    for m in modules:
#        m.add_eventcallback(core.handle_event)
#        core.add_events(m.get_events())
#        core.add_actions(m.get_actions())
#
#    # Register all jobs
#    core.add_jobs(jobs)
#
#    # Setup the services
#    for m in modules:
#        m.setup()
#
#    # Shutdown setup
#    def close():
#        mr = modules[:]
#        mr.reverse()
#        for m in mr:
#            m.close()
#
#    reactor.addSystemEventTrigger('before','shutdown',close)
#
#    # Start everything
#    log.msg('Server PID: %s' %(os.getpid()), system='MAIN')
#    reactor.run()

import os,sys,atexit
from twisted.internet import reactor
from twisted.python import log, syslog
from core import Core


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
def main(modules,jobs,use_syslog=False):
    ''' Main Entry poin '''

    if use_syslog:
        syslog.startLogging(prefix='Lumina')
    else:
        log.startLogging(sys.stdout)

    # Main server handler
    core = Core()

    # Register all modules
    for m in modules:
        m.add_eventcallback(core.handle_event)
        core.add_events(m.get_events())
        core.add_actions(m.get_actions())

    # Register all jobs
    core.add_jobs(jobs)

    # Setup the services
    for m in modules:
        m.setup()

    # Shutdown setup
    def close():
        mr = modules[:]
        mr.reverse()
        for m in mr:
            m.close()

    reactor.addSystemEventTrigger('before','shutdown',close)

    # Start everything
    log.msg('Server PID: %s' %(os.getpid()), system='MAIN')
    reactor.run()

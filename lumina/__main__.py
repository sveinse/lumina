# -*- python -*-
from __future__ import absolute_import

import os
import sys
import atexit
import argparse
import setproctitle
from twisted.internet import reactor

from lumina import log
from lumina.lumina import Lumina


#===  Become DAEMON
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
        sys.stderr.write("%s: pidfile '%s' exists. Refusing to start daemon\n" %(
            sys.argv[0],pidfile))
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



#===  MAIN function
def main(args=None):


    #==  PARSE ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument('-c', '--config', default=None, metavar='CONFIG', help='Read configuration file')
    if os.name != 'nt':
        ap.add_argument('--pidfile', default='/var/run/lumid.pid', metavar='FILENAME', help='Set the pidfile')
        ap.add_argument('--daemon', action='store_true', help='Daemonize application')
        ap.add_argument('--syslog', action='store_true', default=False, help='Enable syslog logging')
    opts = ap.parse_args()


    #==  SET PROC TITLE
    setproctitle.setproctitle('lumina')

    #==  DAEMONIZE
    if os.name != 'nt' and opts.daemon:
        daemonize(pidfile=opts.pidfile)
        opts.syslog=True

    #==  LOGGING
    log.startLogging(syslog=(os.name != 'nt' and opts.syslog),syslog_prefix='Lumina')
    log.Logger(namespace='-').info("PID {pid}", pid=os.getpid())

    #== MAIN
    #   This will load the plugins and set them up
    main = Lumina()
    main.setup(conffile=opts.config)

    #== START TWISTED
    reactor.run()

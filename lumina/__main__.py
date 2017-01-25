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
    ''' Make the running process into a daemon process by disconnecting its file
        in/out and by forking. '''

    try:
        with file(pidfile, 'r') as pidf:
            pid = int(pidf.read().strip())
    except IOError:
        pid = None
    if pid:
        sys.stderr.write("%s: pidfile '%s' exists. Refusing to start daemon\n" %(
            sys.argv[0], pidfile))
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
    stdin = file('/dev/null', 'r')
    stdout = file('/dev/null', 'a+')
    stderr = file('/dev/null', 'a+', 0)
    os.dup2(stdin.fileno(), sys.stdin.fileno())
    os.dup2(stdout.fileno(), sys.stdout.fileno())
    os.dup2(stderr.fileno(), sys.stderr.fileno())

    # Write pidfile and register a cleanup-function for it
    def delpid():
        ''' Remove the pidfile '''
        try:
            os.remove(pidfile)
        except OSError:
            pass

    atexit.register(delpid)
    file(pidfile, 'w+').write(str(os.getpid()) + '\n')



#===  MAIN function
def main(args=None):
    ''' Lumina main function '''

    #==  PARSE ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument('-c', '--config', default=None, metavar='CONFIG',
                    help='Read configuration file')
    if os.name != 'nt':
        ap.add_argument('--pidfile', default='/var/run/lumid.pid', metavar='FILENAME',
                        help='Set the pidfile')
        ap.add_argument('--daemon', action='store_true',
                        help='Daemonize application')
        ap.add_argument('--syslog', action='store_true', default=False,
                        help='Enable syslog logging')
    opts = ap.parse_args()


    #==  SET PROC TITLE
    setproctitle.setproctitle('lumina')

    #==  DAEMONIZE
    if os.name != 'nt' and opts.daemon:
        daemonize(pidfile=opts.pidfile)
        opts.syslog = True

    #==  LOGGING
    log.startLogging(syslog=(os.name != 'nt' and opts.syslog), syslog_prefix='Lumina')

    #== MAIN
    #   This will load the plugins and set them up
    lumina = Lumina()
    lumina.setup(conffile=opts.config)

    #== START TWISTED
    reactor.run()

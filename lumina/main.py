# -*- python -*-
""" Main dispatcher for Lumina """
from __future__ import absolute_import, division, print_function

import os
import sys
import atexit
import argparse
import setproctitle

from twisted.internet import reactor
from twisted.logger import LogLevel

import lumina
from lumina import log
from lumina.lumina import Lumina, LuminaClient
from lumina.config import Config



#===  Detach DAEMON
def detach(pidfile):
    ''' Make the running process into a detached process by disconnecting its
        file in/out and by forking. '''

    try:
        with open(pidfile, 'r') as pidf:
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
    stdin = open('/dev/null', 'r')
    stdout = open('/dev/null', 'a+')
    stderr = open('/dev/null', 'a+', 0)
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
    open(pidfile, 'w+').write(str(os.getpid()) + '\n')


#===  COMMANDS

def client(parser, opts, cmd):
    ''' Client command '''

    # Logging
    loglevel = opts.loglevel or 'error'
    log.start(syslog=False,
              redirect_stdio=False,
              loglevel=LogLevel.levelWithName(loglevel))

    # Load configuration
    config = Config()
    config['plugins'] = ['client']
    if opts.config:
        config.readconfig(opts.config)
        config['conffile'] = opts.config

    # Initiate Lumina client engine, select reactor here
    master = LuminaClient(reactor, config=config)
    reactor.callLater(0, master.run, cmd)

    # Start Twisted reactor
    master.log.info("Starting reactor")
    reactor.run()
    return master.return_value


def server(parser, opts, cmd):
    ''' Run the Lumina server '''

    # Detach server
    if sys.platform != 'win32' and opts.detach:
        detach(pidfile=opts.pidfile)
        opts.syslog = True

    # Logging
    loglevel = opts.loglevel or 'debug'
    log.start(syslog=(sys.platform != 'win32' and opts.syslog),
              redirect_stdio=True,
              loglevel=LogLevel.levelWithName(loglevel))

    # Load configuration
    config = Config()
    if opts.config:
        config.readconfig(opts.config)
        config['conffile'] = opts.config

    # Initiate Lumina engine, select reactor here
    master = Lumina(reactor, config=config)
    reactor.callLater(0, master.run)

    # Start Twisted reactor
    master.log.info("Starting reactor")
    reactor.run()
    return master.return_value


def print_help(parser, opts, cmd):
    ''' Print command help '''
    help = HelpAction(None, None, None)
    help(parser, None, None)


COMMANDS = {
    'client': client,
    'help': print_help,
    'server': server,
}


class HelpAction(argparse.Action):
    ''' Custom help printer '''
    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()
        print("\nLumina commands:")
        for command in COMMANDS:
            print("  %-16s     %s" %(command, COMMANDS[command].__doc__))
        parser.exit()


#===  MAIN function
def main(args=None):    # pylint: disable=W0613
    ''' Lumina main function '''

    # Parse args
    parser = argparse.ArgumentParser(description=lumina.__doc__, add_help=False,
                                     prog='lumina')
    parser.add_argument('--help', action=HelpAction, nargs=0,
                        help='show this help message and exit')
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + lumina.__version__ +
                        ' build ' + lumina.__build__)
    parser.add_argument('-c', '--config', default=None, metavar='CONFIG',
                        help='Read configuration file')
    parser.add_argument('--loglevel', default=None, metavar='LOGLEVEL',
                        help='Set loglevel')
    #parser.add_argument('--server', action='store_true',
    #                    help='Run Lumina server. Any commands given will be ignored')
    if sys.platform != 'win32':
        parser.add_argument('--pidfile', default='/var/run/lumid.pid',
                            metavar='FILENAME',
                            help='(Server only) set the pidfile')
        parser.add_argument('--detach', action='store_true',
                            help='(Server only) detach application')
        parser.add_argument('--syslog', action='store_true', default=False,
                            help='(Server only) Enable syslog logging')
    parser.add_argument('command', default=None, nargs='?',
                        help='Command to run (ignored if --server)')

    opts = parser.parse_args()

    # Set proc title
    setproctitle.setproctitle('lumina')

    # Handle command
    cmd = opts.command
    if cmd is None:
        parser.error('Missing required command')

    elif cmd in COMMANDS:
        return COMMANDS[cmd](parser, opts, cmd)

    else:
        parser.error('Unknown command: ' + cmd)

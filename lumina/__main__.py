# -*- python -*-
from __future__ import absolute_import

import os
import sys
import atexit
import argparse
from importlib import import_module
from twisted.python import log
from twisted.internet import reactor

from .config import Config



#===  CONFIG DEFAULTS
CONFIG = {
    'services' : dict( default=('controller',), help='Services to run', type=tuple ),
    'plugins'  : dict( default=( ), help='Client plugins to start', type=tuple ),
    'conffile' : dict( default='lumina.conf', help='Configuration file' ),
}


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


    #==  DAEMONIZE
    if os.name != 'nt' and opts.daemon:
        daemonize(pidfile=opts.pidfile)
        opts.syslog=True


    #==  LOGGING
    if os.name != 'nt' and opts.syslog:
        from twisted.python import syslog
        syslog.startLogging(prefix='Lumina')
    else:
        log.startLogging(sys.stdout)


    #== CONFIGUATION
    config = Config(settings=CONFIG)

    # Load new config
    if opts.config:
        config.readconfig(opts.config)
        config.set('conffile', opts.config)


    #== SERVICES
    services = config['services']
    central = None


    #== MAIN SERVER ROLE
    if 'controller' in services:

        from .controller import Controller
        from .logic import Logic
        from .web import Web

        # Main controller
        controller = Controller()
        config.amend(controller.CONFIG)
        controller.setup(config=config)

        # Logic/rules handler (FIXME)
        logic = Logic()
        logic.setup()
        controller.add_jobs(logic.jobs)
        controller.add_commands(logic.alias)

        # Web server
        web = Web()
        config.amend(web.CONFIG)
        web.setup(controller, config=config)

        # Set the controller as the plugin central
        central = controller


    #== CLIENT ROLE(S)
    if 'client' in services:

        from client import Client

        # Client controller
        client = Client()
        config.amend(client.CONFIG)
        client.setup(config=config)

        # Set the client as the plugin central
        central = client


    #== PLUGINS
    for name in config['plugins']:

        # Ignore empty plugin names
        name = name.strip()
        if not len(name):
            continue

        # No plugins if we don't have a central
        if not central:
            log.msg("No central to register %s to" %(name), system='-')
            continue

        # Load module and find main object
        log.msg("Loading plugin %s" %(name), system=central.system)

        plugin = import_module('lumina.plugins.' + name).PLUGIN()

        log.msg("===  Registering endpoint %s" %(plugin.name), system=central.system)

        # Setup events and commands. configure() sets the plugins events and commands
        plugin.configure()
        plugin.add_eventcallback(central.handle_event)
        central.add_events(plugin.get_events())
        central.add_commands(plugin.get_commands())

        # Register settings and prepare the plugin to run
        config.amend(plugin.CONFIG)
        plugin.setup(config=config)

        # Setup for closing the plugin on close
        reactor.addSystemEventTrigger('before','shutdown',plugin.close)
        central.endpoints.append(plugin)


    #== START TWISTED
    log.msg('Server PID: %s' %(os.getpid()), system='-')
    reactor.run()

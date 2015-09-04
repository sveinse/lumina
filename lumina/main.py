# -*- python -*-
import os,sys,atexit
import socket
from twisted.python import log
from importlib import import_module

from config import Config


#===  CONFIG DEFAULTS
CONFIG_DEFAULTS = dict(
    services          = 'controller client',
    port              = '8081',
    name              = 'CLIENT',
    server            = 'localhost',
    plugins           = '',
    web_port          = '8080',
    web_root          =  os.getcwd()+'/www',
)


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



#===  Parse config
def readconfig(configfile):

    #== CONFIGUATION
    config = Config(defaults=CONFIG_DEFAULTS)
    if configfile:
        config.readconfig(configfile)

    return config



#===  MAIN function
def main(config):

    #== SERVICES
    services = config['services']


    #== MAIN SERVER ROLE
    if 'controller' in services:

        from controller import Controller
        from logic import Logic
        from web import Web

        # Main controller
        port = int(config['port'])
        controller = Controller(port=port)
        controller.setup()

        # Logic/rules handler
        logic = Logic()
        logic.setup()
        controller.add_jobs(logic.jobs)
        controller.add_commands(logic.alias)

        # Web server
        wport = int(config['web_port'])
        wroot = config['web_root']
        web = Web(port=wport,webroot=wroot)
        web.setup(controller)


    #== CLIENT ROLE(S)
    if 'client' in services:

        from client import Client

        # Client controller
        client = Client(host=config['server'],port=int(config['port']),name=config['name'])
        client.setup()

        # Plugins
        for name in config.get('plugins',[]):

            # Ignore empty plugin names
            name = name.strip()
            if not len(name):
                continue

            # Load module and find main object
            mod = import_module('lumina.plugins.' + name)
            plugin = mod.PLUGIN(config)

            # Register function
            client.register(plugin)

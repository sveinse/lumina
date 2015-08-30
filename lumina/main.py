# -*- python -*-
import os,sys,atexit
import socket
from twisted.python import log
from importlib import import_module


# CONFIG DEFAULTS
CONFIG_DEFAULTS = dict(
    services          = 'controller client',
    port              = '8081',
    name              = 'CLIENT',
    server            = 'localhost',
    plugins           = '',
    web_port          = '8080',
    web_root          =  os.getcwd()+'/www',
)


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



#
# ***  CONFIGURATION FILE  ***
#
def parseconfig(f):
    conf = {}
    n=0
    for line in f:
        try:
            n+=1
            line = line.strip()

            if not len(line):
                continue
            if line.startswith('#'):
                continue

            # Split on =. Allow only one =
            li = line.split('=')
            if len(li) < 2:
                raise Exception("Syntax error")
            if len(li) > 2:
                raise Exception("Syntax error")

            # Remove leading and trailing whitespaces
            key  = li[0].strip()
            data = li[1].strip()

            # Do not accept empty key names
            if not len(key):
                raise Exception("Syntax error")

            # Remove trailing AND leading ". Fail if " is in string
            if len(data)>1 and data.startswith('"') and data.endswith('"'):
                data=data[1:-1]
            if '"' in data[1]:
                raise Exception("Syntax error")

            key = key.lower()
            if key in conf:
                raise Exception("Config already set")
            conf[key] = data

        except Exception as e:
            raise Exception("%s:%s: %s '%s'" %(configfile,n,e.message,line))
    return conf



def readconfig(configfile):

    conf = {}
    if configfile:
        try:
            with open(configfile,'r') as f:
                conf = parseconfig(f)
        except:
            raise

    # Set default values and override from user config
    config = CONFIG_DEFAULTS.copy()
    config.update(conf)

    # SPLIT ON SPACE
    for k,d in config.items():
        if k in ( 'services', 'modules', 'plugins' ):
            config[k] = tuple(d.split(' '))

    # SPLIT ON :
    #for k,d in config.items():
    #    if k in ( 'server' ):
    #        config[k] = tuple(d.split(':'))

    return config



#
# ***  MAIN FUNCTION  ***
#
def main(config):

    services = config['services']

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

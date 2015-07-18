# -*- python -*-
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
    obj.register()
    parent.add_events(obj.get_events())
    parent.add_commands(obj.get_commands())
    obj.setup()
    reactor.addSystemEventTrigger('before','shutdown',obj.close)


#
# ***  CONTROLLER  ***
#
def controller():

    from controller import Controller
    from logic import Logic
    #from utils import Utils
    #from telldus import Telldus

    # Main controller
    controller = Controller(port=8081)
    controller.setup()

    # Logic/rules handler
    logic = Logic()
    logic.setup()
    controller.add_jobs(logic.jobs)

    # System Functions
    #register(controller, Utils())
    #register(controller, Telldus())



#
# ***  CLIENT LYS  ***
#
def client_lys():

    from client import Client
    from ep_telldus import Telldus
    from ep_oppo import Oppo
    from ep_demo import Demo
    from ep_yamaha import Yamaha

    # Main controller
    controller = Client(host='localhost',port=8081,name='LYS')
    controller.setup()

    # System Functions
    register(controller, Telldus())
    register(controller, Oppo('/dev/ttyUSB0'))
    register(controller, Yamaha('192.168.234.20'))



#
# ***  CLIENT HW50  ***
#
def client_hw50(host,port):

    from client import Client
    from ep_hw50 import Hw50
    from ep_led import Led

    # Main controller
    controller = Client(host=host,port=port,name='HW50')
    controller.setup()

    # System Functions
    register(controller, Hw50('/dev/ttyUSB0'))
    register(controller, Led())



#
# ***  TEST  ***
#
def test():

    from controller import Controller
    from client import Client
    from logic import Logic
    from ep_utils import Utils
    from ep_telldus import Telldus
    from ep_demo import Demo
    from ep_yamaha import Yamaha

    # Main controller
    if True:
        controller = Controller(port=8081)
        controller.setup()

        # Logic/rules handler
        #logic = Logic()
        #logic.setup()
        #controller.add_jobs(logic.jobs)

        #register(controller, Demo())
        register(controller, Yamaha('192.168.234.20'))

    # Main client
    if False:
        controller = Client(host='localhost',port=8081,name='test')
        controller.setup()

        #register(controller, Demo())
        register(controller, Yamaha('192.168.234.20'))

    if False:
        def pr(val):
            print 'RESPONSE',val
        y = Yamaha('192.168.234.20')
        y.setup()
        #d = y.protocol.command('GET', [ 'Main_Zone', 'Volume', 'Lvl' ])
        d = y.get_volume()
        d.addCallback(pr)
        #y.protocol.command('PUT', [ 'Main_Zone', 'Volume', 'Lvl' ], {
        #    'Val': -300,
        #    'Exp': 1,
        #    'Unit': 'dB',
        #} )
        #y.protocol.command('GET', [ 'System', 'Signal_Info' ])

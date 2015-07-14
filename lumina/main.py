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
    reactor.addSystemEventTrigger('before','shutdown',obj.close)


#
# ***  CONTROLLER  ***
#
def controller():

    from controller import Controller
    from utils import Utils
    from logic import Logic
    from telldus import Telldus

    # Main controller
    controller = Controller(port=8081)
    controller.setup()

    # Logic/rules handler
    logic = Logic()
    logic.setup()
    controller.add_jobs(logic.jobs)

    # System Functions
    register(controller, Utils())

    #register(controller, Telldus())



#
# ***  CLIENT LYS  ***
#
def client_lys():

    from client import Client
    from telldus import Telldus
    from oppo import Oppo
    from demo import Demo
    from yamaha import Yamaha

    # Main controller
    controller = Client(host='localhost',port=8081,name='LYS')
    controller.setup()

    # System Functions
    register(controller, Telldus())
    register(controller, Oppo('/dev/ttyUSB0'))
    #register(controller, Yamaha('192.168.234.20'))



#
# ***  CLIENT HW50  ***
#
def client_hw50(host,port):

    from client import Client
    from hw50 import Hw50
    from led import Led

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
    from utils import Utils
    from logic import Logic
    from telldus import Telldus
    from demo import Demo
    from yamaha import Yamaha

    # Main controller
    if False:
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

    if True:
        y = Yamaha('192.168.234.20')
        y.setup()
        y.protocol.command()



################################################################
#
#  TESTING
#
################################################################
if __name__ == "__main__":

    import os,sys
    from twisted.python import log
    from twisted.internet import reactor

    from client import Client
    from hw50 import Hw50
    from oppo import Oppo
    from utils import Utils
    from controller import Controller

    log.startLogging(sys.stdout)

    #controller()

    # Main controller
    controller = Controller(port=8081)
    controller.setup()

    # Main controller
    #controller = Client(host='localhost',port=8081,name='lys')
    #controller.setup()

    # System Functions
    #register(controller, Utils())
    #register(controller, Telldus())
    register(controller, Oppo('/dev/ttyUSB0'))

    log.msg('Server PID: %s' %(os.getpid()), system='CTRL')
    reactor.run()

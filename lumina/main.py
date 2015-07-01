import os,sys,atexit
from twisted.internet import reactor
from twisted.python import log, syslog
#from core import Core
from core import JobFn
from utils import Utils


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



def gen():
    print 'GENERATOR START'
    yield 'delay{2}'
    status = yield 'hw50/status_power'
    print 'STATUS', status
    lamp = yield 'hw50/lamp_timer'
    print 'LAMP', lamp
    yield 'stop'


jobs = {
    # Event -> Action(s)

    # Global events
    'starting'       : None,
    'stopping'       : None,

    # Telldus connections
    'td/starting'    : None,
    'td/connected'   : None,
    'td/error'       : None,

    # Oppo connections
    'oppo/starting'  : None,
    'oppo/connected' : None,
    'oppo/error'     : None,

    # Nexa fjernkontroll
    'remote/g/on'    : ( 'kino/led/on', 'kino/lys/on' ),
    'remote/g/off'   : ( 'kino/lys/off' ),
    'remote/3/on'    :   'kino/tak-reol/dim{30}',
    'remote/3/off'   :   'kino/tak-reol/off',
    'remote/4/on'    :   'kino/lys/dim{30}',
    'remote/4/off'   : ( 'kino/tak/off', 'kino/bord/dim{30}' ),

    #'remote/1/on'   :   'oppo/play',
    'remote/1/off'   : ( 'kino/lys/off', 'oppo/off' ),

    # Veggbryter overst hjemmekino
    'wallsw1/on'     : ( 'kino/led/on', 'kino/lys/on' ),
    'wallsw1/off'    : ( 'kino/lys/off', ),

    # Veggbryter nederst kino
    'wallsw2/on'     :   'kino/lys/dim{30}',
    'wallsw2/off'    : ( 'kino/lys/off', 'kino/led/off' ),

    # Oppo regler
    'oppo/pause'     :   'kino/lys/dim{30}',
    'oppo/play'      :   'kino/lys/off',
    'oppo/stop'      :   'kino/lys/dim{60}',

    # Temperatur
    'temp/ute'       : None,
    'temp/kjeller'   : None,
    'temp/loftute'   : None,
    'temp/kino'      : None,
    'temp/fryseskap' : None,

    'test' : JobFn(gen),
    'stop' : 'stop',
    'b': 'y',
    'c': ('w','x','y','y2','z'),
}


#
# ***  CONTROLLER  ***
#
def controller(use_syslog=False):

    from controller import Controller

    if use_syslog:
        syslog.startLogging(prefix='Lumina')
    else:
        log.startLogging(sys.stdout)

    controller = Controller(www_port=8080,socket_port=8081)
    controller.setup()
    controller.add_jobs(jobs)

    utils = Utils()
    utils.add_eventcallback(controller.handle_event)
    controller.add_events(utils.get_events())
    controller.add_actions(utils.get_actions())
    utils.setup()

    # Start everything
    log.msg('Server PID: %s' %(os.getpid()), system='CTRL')
    reactor.run()



from callback import Callback
from twisted.internet.task import LoopingCall
from core import Event
from twisted.internet.defer import Deferred


class Demo(object):

    def __init__(self):
        self.cbevent = Callback()

    def setup(self):
        self.loop = LoopingCall(self.loop_cb)
        #self.loop.start(20, False)

    # -- Event handler
    def add_eventcallback(self, callback, *args, **kw):
        self.cbevent.addCallback(callback, *args, **kw)
    def event(self,event,*args):
        self.cbevent.callback(Event(event,*args))

    # -- List of supported event and actions
    def get_events(self):
        return [ 'a', 'b', 'c' ]

    def get_actions(self):
        return {
            'x' : lambda a : log.msg("X run"),
            'y' : lambda a : self.delay(Event('y{1,2,3}')),
            'y2' : lambda a : self.delay('y2'),
            'z' : lambda a : log.msg("Z run"),
            'w' : lambda a : 'abcd',
        }

    # -- Worker
    def loop_cb(self):
        self.event('a')

    def delay(self,data):
        self.d = Deferred()
        reactor.callLater(2,self.done,data)
        return self.d

    def done(self,data):
        self.d.callback(data)


def register(parent,obj):
    obj.add_eventcallback(parent.handle_event)
    parent.add_events(obj.get_events())
    parent.add_actions(obj.get_actions())
    obj.setup()


#
# ***  CLIENT  ***
#
def client(use_syslog=False):

    from client import Client

    if use_syslog:
        syslog.startLogging(prefix='Lumina')
    else:
        log.startLogging(sys.stdout)

    # Main controller
    cli = Client(host='localhost',port=8081,name='demo')
    cli.setup()

    demo = Demo()
    register(cli,demo)

    # Start everything
    log.msg('Server PID: %s' %(os.getpid()), system='MAIN')
    reactor.run()

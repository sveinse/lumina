# -*-python-*-
import os,sys

from twisted.internet import reactor
from twisted.python import log
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.internet.defer import Deferred
from callback import Callback

# Can be tested with
#    socat UNIX-LISTEN:/tmp/TelldusEvents -
#    socat UNIX-LISTEN:/tmp/TelldusClient -
#
# On target communicting with Telldus:
#     socat UNIX-connect:/tmp/TelldusEvents -
#     socat UNIX-connect:/tmp/TelldusClient -



def getnextelement(data):
    ''' Return the (next,remain) raw data element from data.

        The syntax is:  NN:string  where NN is a number indicating length of string
                        iNs        where N is am integer number
    '''
    if data and data[0] in '0123456789':
        n = data.split(':',1)
        l = int(n[0])
        return (n[1][:l], n[1][l:])
    elif data and data[0]=='i':
        n = data.split('s',1)
        #log.msg(n)
        l = int(n[0][1:])
        return (l,n[1])
    else:
        return (None,data)



def parsestream(data):
    ''' Parse self.data byte stream into list of elements in self.elements '''
    el = [ ]

    # Split the raw data into list of objects (string or integer)
    while True:
        (element,data) = getnextelement(data)
        if element is None:
            return el,data
        el.append(element)



def parseelements(elements):
    ''' Parse elements into events '''
    events = [ ]

    # Extract events from list of objects
    while elements:
        cmd = elements.pop(0)
        #log.msg("%s  %s" %(cmd,elements))

        # Expected commands and their parameter length
        cmdsize = {
            'TDSensorEvent': 6,
            'TDRawDeviceEvent': 2,
            'TDControllerEvent': 4,
            'TDDeviceEvent': 3,
        }

        if cmd not in cmdsize:
            log.msg("Unknown command '%s', dropping %s" %(cmd, elements))
            elements = [ ]
            break

        l = cmdsize[cmd]

        if l > len(elements):
            # Does not got enough data for command. Stop and postpone processing
            log.msg("Missing elements for command '%s', got %s, needs %s args." %(cmd,elements,l))
            elements = [ ]
            break

        l = cmdsize[cmd]
        args = elements[:l]
        elements = elements[l:]
        events.append( [cmd] + args )

    return (events, elements)



def parserawargs(args):
    ''' Split the 'key1:data1;key2:data2;...' string syntax into a dictionary '''

    alist = args.split(';')
    adict = dict()
    for a in alist:
        if a:
            o = a.split(':')
            adict[o[0]]=o[1]
    return adict



def generate(args):
    s=''
    for a in args:
        if type(a) is str:
            s+='%s:%s' %(len(a),a)
        elif type(a) is int:
            s+='i%ds' %(a)
    return s



class TelldusFactory(ClientFactory):
    def __init__(self, protocol, parent):
        self.protocol = protocol
        self.parent = parent

    def buildProtocol(self, addr):
        return self.protocol

    def clientConnectionFailed(self, connector, reason):
        self.parent.error(self, reason)



class TelldusEvents(Protocol):
    name = 'Event'
    path = '/tmp/TelldusEvents'

    def __init__(self,parent):
        self.parent = parent
        self.connected = False

    def connect(self):
        factory = TelldusFactory(self, self.parent)
        reactor.connectUNIX(self.path, factory)
        self.factory = factory

    def connectionMade(self):
        log.msg("%s connected" %(self.name))
        self.data = ''
        self.elements = [ ]
        self.connected = True

    def connectionLost(self, reason):
        log.msg("%s connection lost" %(self.name), reason)
        if self.connected:
            self.connected = False
            self.parent.error(self,reason)

    def disconnect(self):
        if self.connected:
            self.connected = False
            self.transport.loseConnection()

    def dataReceived(self, data):
        log.msg("     >>>  (%s)'%s'" %(len(data),data))

        data = self.data + data

        # Interpret the data
        (elements, data) = parsestream(data)
        (events, elements) = parseelements(elements)

        # Save remaining data (incomplete frame received)
        self.data = data
        self.elements = elements

        # Iverate over the events
        for event in events:
            cmd = event[0]

            log.msg("     ---  %s  %s" %(cmd,event[1:]))

            if cmd == 'TDRawDeviceEvent':
                #log.msg("RAW event", event)

                args = parserawargs(event[1])
                if 'protocol' not in args:
                    log.msg("Missing protocol from %s, dropping event" %(cmd))
                    continue

                if args['protocol'] != 'arctech':
                    #og.msg("Ignoring unknown protocol '%s' in '%s', dropping event" %(args['protocol'],cmd))
                    continue

                # Pass on to factory to call the callback
                self.parent.event(cmd, args)

            # Ignore the other events
            #log.msg("Ignoring unhandled command '%s', dropping" %(cmd))



class TelldusClient(Protocol):
    name = 'Client'
    path = '/tmp/TelldusClient'
    queue = [ ]
    active = None

    def __init__(self,parent):
        self.parent = parent
        self.data = ''
        self.elements = [ ]
        self.connected = False

        self.factory = TelldusFactory(self, self.parent)

    def connect(self):
        #factory = TelldusFactory(self, self.parent)
        reactor.connectUNIX(self.path, self.factory)
        #self.factory = factory

    def connectionMade(self):
        log.msg("%s connected" %(self.name))
        self.data = ''
        self.elements = [ ]
        self.connected = True
        (data,d) = self.active
        log.msg("     <<<  (%s)'%s'" %(len(data),data))
        self.transport.write(data)

    def connectionLost(self, reason):
        log.msg("%s connection closed" %(self.name))
        self.connected = False
        self.active = None
        self.sendNextCommand()

    def disconnect(self):
        if self.connected:
            self.transport.loseConnection()

    def dataReceived(self, data):
        log.msg("     >>>  (%s)'%s'" %(len(data),data))

        data = self.data + data
        (elements, data) = parsestream(data)

        log.msg("     ---  %s" %(elements))
        (m,d) = self.active
        self.disconnect()
        d.callback(elements)

    def sendCommand(self, cmd):
        data = generate(cmd)
        d = Deferred()
        self.queue.append( (data, d) )
        self.sendNextCommand()
        return d

    def sendNextCommand(self):
        if not self.queue:
            return
        if self.active:
            return
        self.active = self.queue.pop(0)
        self.connect()



class Telldus:
    queue = [ ]
    active = None

    def __init__(self):
        self.cbevent = Callback()
        self.cberror = Callback()
        self.cbready = Callback()

        self.events = TelldusEvents(self)
        self.client = TelldusClient(self)

        reactor.addSystemEventTrigger('before','shutdown',self.close)


    def setup(self):
        self.events.connect()
        #self.client.connect()


    def close(self):
        log.msg("Close called")
        if self.events:
            self.events.disconnect()
        if self.client:
            self.client.disconnect()


    # Protocol and factory entry points
    def error(self, who, reason):
        log.msg("Received error: ",who,reason)
        if not self.cberror.fired:
            self.cberror.callback(reason)

    def connected(self, who):
        self.cbready.callback(None, condition=self.events.connected and self.client.connected)

    def event(self,cmd,args):
        self.cbevent.callback( (cmd,args) )


    # Observer callbacks
    def addCallbackReady(self, callback, *args, **kw):
        self.cbready.addCallback(callback, *args, **kw)
    def addCallbackError(self, callback, *args, **kw):
        self.cberror.addCallback(callback, *args, **kw)
    def addCallbackEvent(self, callback, *args, **kw):
        self.cbevent.addCallback(callback, *args, **kw)



    def sendCommand(self, cmd):
        data = generate(cmd)
        d = Deferred()
        self.queue.append( (data, d) )
        if not self.active:
            self.sendNextCommand()
        return d

    def sendNextCommand(self):
        if not self.queue:
            return
        self.active = self.queue.pop(0)
        (data,d) = self.active
        #log.msg("     <<<  (%s)'%s'" %(len(data),data))
        #self.transport.write(data)
        # TBD

        #client = self.client
        #factory = TelldusFactory(client, self)
        #reactor.connectUNIX('/tmp/TelldusClient')


    # Actions
    def turnOn(self,num):
        cmd = ( 'tdTurnOn', num )
        return self.client.sendCommand(cmd)

    def turnOff(self,num):
        cmd = ( 'tdTurnOff', num )
        return self.client.sendCommand(cmd)

    def dim(self,num, val):
        cmd = ( 'tdDim', num, val )
        return self.client.sendCommand(cmd)



if __name__ == "__main__":
    from twisted.python.log import startLogging
    startLogging(sys.stdout)

    def error(reason,td):
        log.msg("ERROR",reason)
        reactor.stop()

    def ready(result,td):
        log.msg("READY",result)
        d = td.turnOn(1)
        d = td.turnOn(2)
        d = td.turnOn(3)

    def event(result,td):
        log.msg("EVENT",result)

    td = Telldus()
    d = td.setup()
    td.addCallbackReady(ready,td)
    td.addCallbackError(error,td)
    td.addCallbackEvent(event,td)
    d = td.turnOn(1)
    d = td.turnOn(2)
    d = td.turnOn(3)

    reactor.run()

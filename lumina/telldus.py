# -*-python-*-
import os,sys

from twisted.internet import reactor
from twisted.python import log
from twisted.internet.protocol import ClientFactory
from twisted.internet.protocol import Protocol
from twisted.internet.defer import Deferred
#from twisted.internet.endpoints import connectProtocol, UNIXClientEndpoint
from deferred import MyDeferred



class TelldusProtocol(Protocol):
    data = ''
    elements = [ ]

    def parsestream(self, data):
        ''' Parse self.data byte stream into list of elements in self.elements '''
        el = [ ]

        # Split the raw data into list of objects (string or integer)
        while True:
            (element,data) = self.nextelement(data)
            if element is None:
                return el,data
            el.append(element)


    def nextelement(self, data):
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


    def parserawargs(self,args):
        ''' Split the 'key1:data1;key2:data2;...' string syntax into a dictionary '''

        alist = args.split(';')
        adict = dict()
        for a in alist:
            if a:
                o = a.split(':')
                adict[o[0]]=o[1]
        return adict


    def parseelements(self, elements):
        ''' Parse self.elements into self.events '''
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


    def handleevents(self, events):
        ''' Handle events '''
        for event in events:
            cmd = event[0]

            log.msg("     ---  %s  %s" %(cmd,event[1:]))

            if cmd == 'TDRawDeviceEvent':
                #log.msg("RAW event", event)

                args = self.parserawargs(event[1])
                if 'protocol' not in args:
                    log.msg("Missing protocol from %s, dropping event" %(cmd))
                    continue

                if args['protocol'] != 'arctech':
                    #og.msg("Ignoring unknown protocol '%s' in '%s', dropping event" %(args['protocol'],cmd))
                    continue

                # Pass on to factory to call the callback
                self.factory.receivedEvent(cmd, args)

            # Ignore the other events
            #log.msg("Ignoring unhandled command '%s', dropping" %(cmd))


    def generate(self, args):
        s=''
        for a in args:
            if type(a) is str:
                s+='%s:%s' %(len(a),a)
            elif type(a) is int:
                s+='i%ds' %(a)
        return s



class TelldusEvents(TelldusProtocol):

    def dataReceived(self, data):
        log.msg("     >>>  (%s)'%s'" %(len(data),data))

        data = self.data + data

        (elements, data) = self.parsestream(data)
        (events, elements) = self.parseelements(elements)
        self.handleevents(events)

        self.data = data
        self.elements = elements


class TelldusEventFactory(ClientFactory):
    protocol = TelldusEvents

    def __init__(self, deferred):
        self.deferred = deferred

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)

    def receivedEvent(self, cmd, args):
        if self.deferred is not None:
            d = self.deferred
            d.callback((cmd,args))


class TelldusAction(TelldusProtocol):

    #def connectionMade(self):
    #    data = self.generate(self.factory.cmd)
    #    log.msg("     <<<  (%s)'%s'" %(len(data),data))
    #    self.transport.write(data)

    def dataReceived(self, data):
        log.msg("     >>>  (%s)'%s'" %(len(data),data))

        data = self.data + data

        (elements, data) = self.parsestream(data)
        log.msg(elements)


class TelldusActionFactory(ClientFactory):
    protocol = TelldusAction

    def __init__(self, deferred, cmd):
        self.deferred = deferred
        self.cmd = cmd

    #def clientConnectionFailed(self, connector, reason):
    #    if self.deferred is not None:
    #        d, self.deferred = self.deferred, None
    #        d.errback(reason)

    


def setupEvents():
    d = MyDeferred()
    factory = TelldusEventFactory(d)
    reactor.connectUNIX('/tmp/TelldusEvents', factory)
    return d


def sendEvent(cmd):
    d = Deferred()
    factory = TelldusActionFactory(d, cmd)
    reactor.connectUNIX('/tmp/TelldusClient', factory)
    return d


def turnOn(num):
    cmd = ( 'tdTurnOn', num )
    return sendEvent(cmd)


def turnOff(num):
    cmd = ( 'tdTurnOff', num )
    return sendEvent(cmd)


def dim(num,val):
    cmd = ( 'tdDim', num, val )
    return sendEvent(cmd)

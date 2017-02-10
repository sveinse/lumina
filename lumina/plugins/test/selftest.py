# -*- python -*-
from __future__ import absolute_import

from twisted.internet.task import LoopingCall
from twisted.internet.defer import Deferred
from twisted.internet import reactor

from lumina.node import Node
from lumina.callback import Callback
from lumina.exceptions import ConfigException
from lumina.plugin import Plugin
from lumina.event import Event
from lumina.exceptions import (NodeException, NoConnectionException,
                               TimeoutException, UnknownCommandException)



class A(Node):

    def configure(self):
        self.events = [
            'event'
        ]
        self.commands = {
            'cmd0': lambda a: self.cmd(123),
            'cmd': lambda a: self.cmd(a.args[0]),
            'nonexist': lambda a: self.nonexist(),
            'fail': lambda a: self.fail(),
            'fail_masked': lambda a: self.fail_masked(),
        }

    def ok(self, result, ev=None):
        self.log.info("++++  TEST OK: {r} {e}", r=result, e=ev)
        return result

    def err(self, result, ev=None):
        self.log.info("++++  TEST ERR: {r} {e}", r=result, e=ev)
        return result

    def emit1(self, name, now=False):
        def callback(self):
            self.count += 1
            d = self.emit(name, self.count)
            self.log.info("++++  TEST EMIT {d}", d=d)
            if isinstance(d, Deferred):
                d.addCallback(self.ok)
                d.addErrback(self.err)

        self.count = 0
        self.loop = LoopingCall(callback, self)
        self.loop.start(3, now)

    def cmd(self, count):
        self.log.info("++++  cmd: {c}", c=count)
        return 42

    def request1(self, name, now=False):
        def callback(self):
            ev = Event(name)
            d = self.request_raw(ev)
            self.log.info("++++  REQUEST {d}", d=d)
            d.addCallback(self.ok, ev)
            d.addErrback(self.err, ev)

        self.loop = LoopingCall(callback, self)
        self.loop.start(3, now)

    def fail(self):
        raise Exception("NOPE")

    def fail_masked(self):
        raise NoConnectionException("Not connected")


class B(Node):
    pass



class Selftest(Plugin):
    ''' Selftest Test node '''

    # --- Initialization
    def __init__(self):
        self.a = A()
        self.b = B()


    def setup(self, main):
        Plugin.setup(self, main)

        self.server = server = main.get_plugin_by_module('server')
        if not server:
            raise ConfigException('No server plugin found. Missing server in config?')

        # Patch the server's handle event to this handler
        server.handle_event = self.handle_event

        self.a.name = self.name + '/a'
        self.a.module = self.module + '/a'
        self.a.configure()
        main.config.register(self.a.CONFIG, name=self.a.name)
        self.a.setup(main=main)

        self.b.name = self.name + '/b'
        self.b.module = self.module + '/b'
        self.b.configure()
        main.config.register(self.b.CONFIG, name=self.b.name)
        self.b.setup(main=main)

        self.log.info("START\n\n\n")


        #------------
        #  TESTS
        #------------
        # 01: Test registered event from node
        # RESULT: server ignores event, None is returned
        #self.a.emit1('event')

        # 02: test registered event from node start immediately
        # RESULT: Same as 01
        #self.a.emit1('event', True)

        # 03: Test unregistered event from node
        # RESULT: Same as 01
        #self.a.emit1('event_unreg')

        # 04: Test unregistered event from node, start immediately
        # RESULT: Same as 01
        #self.a.emit1('event_unreg', True)

        # 05: Test commands sent from server
        # RESULT: OK response w/failed UnknownCommandException
        #self.cmd2('test.selftest/a/cmd',False)

        # 06: Test commands sent from server
        # RESULT: ERR + UnknownCommandException
        #self.cmd2('test.selftest/a/cmd',True)

        # 07: Test commanads from server
        # RESULT: OK + 42
        #self.cmd2('test.selftest/a/cmd',True)

        # 08: Test client requesting hostid reply
        # RESULT: OK + [serverid]
        #self.a.request1('serverid')

        # 09: Test events requesting hostid reply, start immediately
        # RESULT: Same as 08
        #self.a.request1('serverid', True)

        # 10: Test commands from server failing
        # RESULT: TB on server, and return error to client
        #self.cmd2('test.selftest/a/nonexist')

        # 11: Test commands from server failing
        #self.cmd2('test.selftest/a/fail')

        # 12: Test commands from server failing
        #self.cmd2('test.selftest/a/fail_masked')

        # 13: Test node issuing command
        #self.a.request1('test.selftest/a/cmd0')

        # 14: Test node issuing failing command
        #self.a.request1('test.selftest/a/fail')

        # 15: Test requesting response on an Event
        self.a.request1('test.selftest/a/event')


    def handle_event(self, event):
        self.log.info("++++  EVENT: {e}",e=event)
        return 7

    def ok(self, result, ev=None):
        self.log.info("++++  TEST OK: {r} {e}", r=result, e=ev)
        return result

    def err(self, result, ev=None):
        self.log.info("++++  TEST ERR: {r} {e}", r=result, e=ev)
        return result

    def cmd2(self, cmd, fail=True):
        def callback(self):
            self.count += 1
            ev = Event(cmd, self.count)
            self.log.info("++++  CALLBACK {c} {e}", c=self.count, e=ev)
            d = self.server.run_command(ev, fail_on_unknown=fail)
            d.addCallback(self.ok,ev)
            d.addErrback(self.err,ev)

        self.count = 0
        self.loop = LoopingCall(callback, self)
        self.loop.start(3, False)




# Main plugin object class
PLUGIN = Selftest

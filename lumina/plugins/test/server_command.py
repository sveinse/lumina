# -*- python -*-
""" Test plugin for testing commands sent directly to the server """
from __future__ import absolute_import, division, print_function

#import traceback

from twisted.internet.defer import Deferred

from lumina.plugin import Plugin
from lumina.node import Node
from lumina.message import Message
from lumina.exceptions import ConfigException


# To test this plugin, use config conf/tests/server_command.json

class ServerCommand(Node):
    """ (TEST) A plugin for generating server commands as direct requests """


    def setup(self):
        self.status.set_GREEN()

        self.master_server = self.master.get_plugin_by_module('server')
        if not self.master_server:
            raise ConfigException("Not running on the server")

        self.runner = self.execute()
        self.master.reactor.callLater(4, self.do_next)



    def execute(self):
        cmds = (
            ('nonexist', 101),      # Test nonexisting command
            ('_name', 102),         # Local command

            ('cmd/1', 201),         # Remote command
            ('cmd/error', 202),     # Remote command with error
            ('cmd/timeout', 203),   # Remote command that returns TimeoutException
            ('cmd/never', 204),     # Test a command that timeout the link
            ('cmd/2', 205),         # Remote command

            ('group/local', 301),  # Local group
            ('group/123', 302),    # Remote group
            ('group/fail', 303),   # Group with failure
            ('group/nonexist', 304),   # Group with failure
        )

        for c in cmds:
            yield ('DIRECT', self.master_server.run_command, c)
            yield ('REMOTE', self.send, c)

    
    def do_next(self):
        try:
            n = self.runner.next()
            self.send_cmd(*n)
        except StopIteration:
            self.master.reactor.stop()


    def send_cmd(self, text, fn, cmd):
        ''' Send command to server and print the response '''
        self.log.info('   ')
        self.log.info('   ')
        self.log.info('---{t}  #{n}--------------------------------', t=text, n=cmd[1])
        m = Message.create('command', cmd[0], *cmd[1:])
        self.log.info('COMMAND: {m}', m=m)
        try:
            d = fn(m)
            self.log.info('  1) RESULT : {d}', d=d)
        except Exception as e:
            self.log.info('  1) FAILED IMMEDIATELY: {c}, {e}', c=e.__class__.__name__, e=e)
            d = None
            #self.log.info('TB={tb}', tb=traceback.format_exc())
        self.log.info('  1) MESSAGE: {m}', m=m)

        if not isinstance(d, Deferred):
            self.log.info('-----------------------------------------------')
            self.do_next()
            return

        def ok(result):
            self.log.info('  2) OK RESULT: {r}', r=result)
        def err(failure):
            self.log.info('  2) ERR RESULT: {r}', r=failure)
        def both(ign):
            self.log.info('  2) MESSAGE  : {m}', m=m)
            self.log.info('-----------------------------------------------')
            self.do_next()

        d.addCallback(ok)
        d.addErrback(err)
        d.addBoth(both)


PLUGIN = ServerCommand

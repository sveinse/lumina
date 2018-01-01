# -*- python -*-
from __future__ import absolute_import

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall

from lumina.plugin import Plugin
from lumina.message import Message
from lumina.exceptions import ConfigException
from lumina.lumina import master


# To test this plugin, use config
#    "plugins": [ "server", "responder", "dir(test.server_command)", "cmd(test.command)" ],
#    "responder.groups": { 
#        "group/123" : [ "cmd/1", "cmd/2", "cmd/3" ],
#        "group/fail" : [ "cmd/1", "cmd/2", "cmd/fail" ]
#     }

class ServerCommand(Plugin):
    """ (TEST) A plugin for generating server commands as direct requests """

    def setup(self):
        self.status.set_GREEN()

        cmds = (
            ('_i', 40),
            ('nonexist',),
            ('cmd/1', 41),
            ('cmd/error', 42),
            ('group/123', 43),
            ('group/fail', 44),
        )
        for i,c in enumerate(cmds):
            reactor.callLater( i*2, self.send_cmd, *c)
        #reactor.callLater(len(cmds)*2, reactor.stop)

        self.master_server = master.get_plugin_by_module('server')
        if not self.master_server:
            raise ConfigException("Not running on the server")


    def send_cmd(self, cmd, *args):
        self.log.info("-----------------------------------------------")
        m = Message.create('command', cmd, *args)
        self.log.info('COMMAND: {m}', m=m)
        d = self.master_server.run_command(m)
        self.log.info("  1) RESULT : {d}", d=d)
        self.log.info('  1) MESSAGE: {m}', m=m)
        if isinstance(d, Deferred):
            def ok(result):
                self.log.info("  2) OK RESULT: {r}", r=result)
                self.log.info('  2) MESSAGE  : {m}', m=m)
                self.log.info("-----------------------------------------------")
            def err(failure):
                self.log.info("  2) ERR RESULT: {r}", r=failure)
                self.log.info('  2) MESSAGE   : {m}', m=m)
                self.log.info("-----------------------------------------------")
            d.addCallback(ok)
            d.addErrback(err)
        else:
            self.log.info("-----------------------------------------------")


PLUGIN = ServerCommand

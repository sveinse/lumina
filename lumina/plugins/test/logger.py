# -*- python -*-
from __future__ import absolute_import

from twisted.internet import reactor
from twisted.internet.defer import Deferred

from lumina.node import Node


class Logger(Node):
    """ (TEST) A plugin for a simple log command """

    # --- Interfaces
    def configure(self):

        self.commands = {
            'log':      lambda a: self.log.info("Logging: {l}", l=a),
        }

    def setup(self):
        self.status.set_GREEN()


PLUGIN = Logger

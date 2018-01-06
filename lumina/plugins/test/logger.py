# -*- python -*-
""" A simple logger test plugin """
from __future__ import absolute_import, division, print_function

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

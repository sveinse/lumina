# -*- python -*-
""" A event test generator plugin that issues undeclared events """
from __future__ import absolute_import, division, print_function

from twisted.internet.task import LoopingCall

from lumina.node import Node


class EventUndeclared(Node):
    """ (TEST) An undeclared event generator """

    # --- Initialization
    def __init__(self):
        self.count = 0

    # --- Interfaces
    def configure(self):

        self.events = (
        )

    def setup(self):
        self.status.set_GREEN()

        self.loop1 = LoopingCall(self.loop_cb1)
        self.loop1.start(4, False)

    # --- Workers
    def loop_cb1(self):
        self.count += 1
        self.sendEvent('undeclared', self.count)


PLUGIN = EventUndeclared

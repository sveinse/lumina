# -*- python -*-
""" A simple timer based event generator plugin """
from __future__ import absolute_import, division, print_function

from twisted.internet.task import LoopingCall

from lumina.node import Node


class EventGenerator(Node):
    """ (TEST) A timer-based event generator """

    # --- Initialization
    def __init__(self):
        self.count = 0

    # --- Interfaces
    def configure(self):

        self.events = (
            'event1',
            'event2',
        )

    def setup(self):
        self.status.set_GREEN()

        self.loop1 = LoopingCall(self.loop_cb1)
        self.loop1.start(3, False)

        self.loop2 = LoopingCall(self.loop_cb2)
        self.loop2.start(4, False)

    # --- Workers
    def loop_cb1(self):
        self.count += 1
        self.sendEvent('event1', self.count)

    def loop_cb2(self):
        self.count += 1
        self.sendEvent('event2', self.count)


PLUGIN = EventGenerator

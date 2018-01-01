# -*- python -*-
from __future__ import absolute_import

from lumina.node import Node


class Null(Node):
    """ (TEST) A minimal do-nothing plugin """

    def setup(self):
        Node.setup(self)
        self.status.set_GREEN()


PLUGIN = Null

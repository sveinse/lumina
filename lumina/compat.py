# -*- python -*-
""" Python3 compatibility """
from __future__ import absolute_import, division, print_function

import sys

# Python 3 compatibility
if sys.version_info < (3, 0):
    STRTYPE = unicode
else:
    STRTYPE = str


def compat_itervalues(dictionary, **kwargs):
    """ Compatibility dictionary iterator """
    try:
        return dictionary.itervalues(**kwargs)
    except AttributeError:
        return dictionary.values(**kwargs)

#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Fix sys.path so it can find our libraries.

This file is named google3.py because gpylint specifically ignores it when
complaining about the order of import statements - google3 should always
come before other non-python-standard imports.
"""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


import os.path
import sys

mydir = os.path.dirname(__file__)
sys.path += [
    os.path.join(mydir, '../..'),
]
import tr.google3  #pylint: disable-msg=W0611,C6204

#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Fix sys.path so it can find our libraries."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import os.path
import sys

mydir = os.path.dirname(__file__)
sys.path = [
    os.path.join(mydir, 'vendor/tornado'),
    os.path.join(mydir, 'vendor/bup/lib'),
    os.path.join(mydir, 'vendor'),
    os.path.join(mydir, '..'),
] + sys.path

#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Fix a weird python relative path import bug."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import sys
import tornado

sys.modules['tornado'] = tornado

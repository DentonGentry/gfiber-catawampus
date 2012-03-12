#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for gmoca.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import base64
import bz2
import tempfile
import unittest

import google3
import gmoca


class GMoCATest(unittest.TestCase):
  """Tests for gmoca.py."""

  def testValidateExports(self):
    gmoca.MOCACTL = 'testdata/device/mocactl'
    gm = gmoca.GMoCA()
    gm.ValidateExports()

  def testDebugOutput(self):
    gmoca.MOCACTL = 'testdata/device/mocactl'
    gm = gmoca.GMoCA()
    out = gm.DebugOutput
    self.assertTrue(len(out) > 1024)
    decode = base64.b64decode(out)  # will raise TypeError if invalid
    decomp = bz2.decompress(decode)
    self.assertTrue(len(decomp) > 1024)
    self.assertTrue(decomp.find('X_GOOGLE-COM_GMOCA') >= 0)


if __name__ == '__main__':
  unittest.main()

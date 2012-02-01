#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for gvsb.py"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3

import gvsb
import tempfile
import unittest

class GvsbTest(unittest.TestCase):
  """Tests for gvsb.py."""

  def testValidateExports(self):
    gv = gvsb.Gvsb()
    gv.ValidateExports()

  def testGvsbServer(self):
    temp = tempfile.NamedTemporaryFile()
    gv = gvsb.Gvsb()
    gv.GVSBSERVERFILE = temp.name
    gv.GvsbServer = "Booga"
    self.assertEqual(gv.GvsbServer, "Booga")
    temp.seek(0)
    self.assertEqual(temp.readline(), "Booga")
    temp.close()

  def testGvsbChannelLineup(self):
    temp = tempfile.NamedTemporaryFile()
    gv = gvsb.Gvsb()
    gv.GVSBCHANNELFILE = temp.name
    gv.GvsbChannelLineup = 1000
    self.assertEqual(gv.GvsbChannelLineup, 1000)
    temp.seek(0)
    self.assertEqual(temp.readline(), "1000")
    temp.close()


if __name__ == '__main__':
  unittest.main()

#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for gvsb.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import tempfile
import unittest

import google3
import gvsb


class GvsbTest(unittest.TestCase):
  """Tests for gvsb.py."""

  def testValidateExports(self):
    gv = gvsb.Gvsb()
    gv.ValidateExports()

  def testGvsbServer(self):
    temp = tempfile.NamedTemporaryFile()
    gvsb.GVSBSERVERFILE = temp.name
    gv = gvsb.Gvsb()
    gv.GvsbServer = 'Booga'
    self.assertEqual(gv.GvsbServer, 'Booga')
    temp.seek(0)
    self.assertEqual(temp.readline(), 'Booga')
    temp.close()

  def testGvsbChannelLineup(self):
    temp = tempfile.NamedTemporaryFile()
    gvsb.GVSBCHANNELFILE = temp.name
    gv = gvsb.Gvsb()
    gv.GvsbChannelLineup = 1000
    self.assertEqual(gv.GvsbChannelLineup, 1000)
    temp.seek(0)
    self.assertEqual(temp.readline(), '1000')
    temp.close()

  def testGvsbKick(self):
    temp = tempfile.NamedTemporaryFile()
    gvsb.GVSBKICKFILE = temp.name
    gv = gvsb.Gvsb()
    gv.GvsbKick = 'kickme'
    self.assertEqual(gv.GvsbKick, 'kickme')
    temp.seek(0)
    self.assertEqual(temp.readline(), 'kickme')
    temp.close()

  def testInitEmptyFiles(self):
    tmpdir = tempfile.mkdtemp()
    gvsb.GVSBSERVERFILE = os.path.join(tmpdir, 'gvsbserverfile')
    gvsb.GVSBCHANNELFILE = os.path.join(tmpdir, 'gvsbchannelfile')
    gvsb.GVSBKICKFILE = os.path.join(tmpdir, 'gvsbkickfile')
    gv = gvsb.Gvsb()
    st = os.stat(gvsb.GVSBSERVERFILE)
    self.assertTrue(st)
    self.assertEqual(st.st_size, 0)
    st = os.stat(gvsb.GVSBCHANNELFILE)
    self.assertTrue(st)
    self.assertEqual(st.st_size, 0)
    st = os.stat(gvsb.GVSBKICKFILE)
    self.assertTrue(st)
    self.assertEqual(st.st_size, 0)
    shutil.rmtree(tmpdir)


if __name__ == '__main__':
  unittest.main()

#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for device_bruno."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import tr.tornadi_fix
import tr.tornado.ioloop
import unittest
import device_bruno

class DeviceBrunoTest(unittest.TestCase):
  """Tests for device_bruno.py."""

  def setUp(self):
    self.old_hnvram = device_bruno.HNVRAM
    self.old_ginstall = device_bruno.GINSTALL
    self.install_cb_called = False

  def tearDown(self):
    device_bruno.HNVRAM = self.old_hnvram
    device_bruno.GINSTALL = self.old_ginstall

  def testGetSerialNumber(self):
    device_bruno.HNVRAM = "testdata/device_bruno/hnvramFOO"
    self.assertEqual(device_bruno.GetNvramParam("FOO"), "123456789")
    device_bruno.HNVRAM = "testdata/device_bruno/hnvramFOO_Empty"
    # We deliberately check against an emtpy string, not assertFalse().
    # Returning None is not acceptable, we want a string.
    self.assertEqual(device_bruno.GetNvramParam("FOO"), '')
    device_bruno.HNVRAM = "testdata/device_bruno/hnvramFOO_Err"
    self.assertEqual(device_bruno.GetNvramParam("FOO"), '')

    device_bruno.HNVRAM = "testdata/device_bruno/hnvramFOO_Empty"
    self.assertEqual(device_bruno.GetNvramParam("FOO", "default"), 'default')
    device_bruno.HNVRAM = "testdata/device_bruno/hnvramFOO_Err"
    self.assertEqual(device_bruno.GetNvramParam("FOO", "default"), 'default')

  def install_callback(self, success):
    self.install_cb_called = True
    self.install_cb_success = success
    tr.tornado.ioloop.IOLoop.instance().stop()

  def testBadInstaller(self):
    device_bruno.GINSTALL = "/dev/null"
    installer = device_bruno.InstallerBruno("/dev/null")
    (code, errstring) = installer.install(self.install_callback)
    self.assertEqual(code, 9001)
    self.assertTrue(errstring)
    self.assertFalse(self.install_cb_called)

  def testInstallerStdout(self):
    device_bruno.GINSTALL = "testdata/device_bruno/installer_128k_stdout"
    installer = device_bruno.InstallerBruno("testdata/device_bruno/imagefile")
    (code, errstring) = installer.install(self.install_callback)
    self.assertEqual(code, 0)
    self.assertFalse(errstring)
    tr.tornado.ioloop.IOLoop.instance().start()
    self.assertTrue(self.install_cb_called)
    self.assertTrue(self.install_cb_success)

  def testInstallerFailed(self):
    device_bruno.GINSTALL = "testdata/device_bruno/installer_fails"
    installer = device_bruno.InstallerBruno("testdata/device_bruno/imagefile")
    (code, errstring) = installer.install(self.install_callback)
    self.assertEqual(code, 0)
    self.assertFalse(errstring)
    tr.tornado.ioloop.IOLoop.instance().start()
    self.assertTrue(self.install_cb_called)
    self.assertFalse(self.install_cb_success)


if __name__ == '__main__':
  unittest.main()

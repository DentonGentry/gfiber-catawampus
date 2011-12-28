#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for device_bruno."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import device_bruno
import os
import tr.tornadi_fix
import tr.tornado.ioloop
import tr.tornado.testing
import unittest

class DeviceBrunoTest(tr.tornado.testing.AsyncTestCase):
  """Tests for device_bruno.py."""

  def setUp(self):
    super(DeviceBrunoTest, self).setUp()
    self.old_hnvram = device_bruno.HNVRAM
    self.old_ginstall = device_bruno.GINSTALL
    self.install_cb_called = False
    self.install_cb_faultcode = None
    self.install_cb_faultstring = None

  def tearDown(self):
    super(DeviceBrunoTest, self).tearDown()
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

  def testBadHnvram(self):
    device_bruno.HNVRAM = "/no_such_binary_at_this_path"
    self.assertEqual(device_bruno.GetNvramParam("FOO"), '')

  def install_callback(self, faultcode, faultstring, must_reboot):
    self.install_cb_called = True
    self.install_cb_faultcode = faultcode
    self.install_cb_faultstring = faultstring
    self.install_cb_must_reboot = must_reboot
    self.stop()

  def testBadInstaller(self):
    device_bruno.GINSTALL = "/dev/null"
    installer = device_bruno.InstallerBruno("/dev/null", ioloop=self.io_loop)
    installer.install(file_type='1 Firmware Upgrade Image',
                      target_filename='',
                      callback=self.install_callback)
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 9002)
    self.assertTrue(self.install_cb_faultstring)

  def testInstallerStdout(self):
    device_bruno.GINSTALL = "testdata/device_bruno/installer_128k_stdout"
    installer = device_bruno.InstallerBruno("testdata/device_bruno/imagefile",
                                            ioloop=self.io_loop)
    installer.install(file_type='1 Firmware Upgrade Image',
                      target_filename='',
                      callback=self.install_callback)
    self.wait()
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 0)
    self.assertFalse(self.install_cb_faultstring)
    self.assertTrue(self.install_cb_must_reboot)

  def testInstallerFailed(self):
    device_bruno.GINSTALL = "testdata/device_bruno/installer_fails"
    installer = device_bruno.InstallerBruno("testdata/device_bruno/imagefile",
                                            ioloop=self.io_loop)
    installer.install(file_type='1 Firmware Upgrade Image',
                      target_filename='',
                      callback=self.install_callback)
    self.wait()
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 9002)
    self.assertTrue(self.install_cb_faultstring)


if __name__ == '__main__':
  unittest.main()

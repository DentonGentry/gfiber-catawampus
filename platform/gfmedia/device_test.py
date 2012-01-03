#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for device.py"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import sys
sys.path.append("../..")

import device
import os
import tr.tornadi_fix
import tr.tornado.ioloop
import tr.tornado.testing
import unittest

class DeviceGFMediaTest(tr.tornado.testing.AsyncTestCase):
  """Tests for device.py."""

  def setUp(self):
    super(DeviceGFMediaTest, self).setUp()
    self.old_hnvram = device.HNVRAM
    self.old_ginstall = device.GINSTALL
    self.install_cb_called = False
    self.install_cb_faultcode = None
    self.install_cb_faultstring = None

  def tearDown(self):
    super(DeviceGFMediaTest, self).tearDown()
    device.HNVRAM = self.old_hnvram
    device.GINSTALL = self.old_ginstall

  def testGetSerialNumber(self):
    device.HNVRAM = "testdata/device/hnvramFOO"
    self.assertEqual(device.GetNvramParam("FOO"), "123456789")
    device.HNVRAM = "testdata/device/hnvramFOO_Empty"
    # We deliberately check against an emtpy string, not assertFalse().
    # Returning None is not acceptable, we want a string.
    self.assertEqual(device.GetNvramParam("FOO"), '')
    device.HNVRAM = "testdata/device/hnvramFOO_Err"
    self.assertEqual(device.GetNvramParam("FOO"), '')

    device.HNVRAM = "testdata/device/hnvramFOO_Empty"
    self.assertEqual(device.GetNvramParam("FOO", "default"), 'default')
    device.HNVRAM = "testdata/device/hnvramFOO_Err"
    self.assertEqual(device.GetNvramParam("FOO", "default"), 'default')

  def testBadHnvram(self):
    device.HNVRAM = "/no_such_binary_at_this_path"
    self.assertEqual(device.GetNvramParam("FOO"), '')

  def install_callback(self, faultcode, faultstring, must_reboot):
    self.install_cb_called = True
    self.install_cb_faultcode = faultcode
    self.install_cb_faultstring = faultstring
    self.install_cb_must_reboot = must_reboot
    self.stop()

  def testBadInstaller(self):
    device.GINSTALL = "/dev/null"
    inst = device.InstallerGFMedia("/dev/null", ioloop=self.io_loop)
    inst.install(file_type='1 Firmware Upgrade Image',
                 target_filename='',
                 callback=self.install_callback)
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 9002)
    self.assertTrue(self.install_cb_faultstring)

  def testInstallerStdout(self):
    device.GINSTALL = "testdata/device/installer_128k_stdout"
    inst = device.InstallerGFMedia("testdata/device/imagefile",
                                           ioloop=self.io_loop)
    inst.install(file_type='1 Firmware Upgrade Image',
                 target_filename='',
                 callback=self.install_callback)
    self.wait()
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 0)
    self.assertFalse(self.install_cb_faultstring)
    self.assertTrue(self.install_cb_must_reboot)

  def testInstallerFailed(self):
    device.GINSTALL = "testdata/device/installer_fails"
    inst = device.InstallerGFMedia("testdata/device/imagefile",
                                           ioloop=self.io_loop)
    inst.install(file_type='1 Firmware Upgrade Image',
                 target_filename='',
                 callback=self.install_callback)
    self.wait()
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 9002)
    self.assertTrue(self.install_cb_faultstring)

  def testGetOneLine(self):
    line = device.GetOneLine('testdata/device/oneline', 'default')
    self.assertEqual(line, 'one')
    line = device.GetOneLine('testdata/device/onelineempty', 'default')
    self.assertEqual(line, '')
    line = device.GetOneLine('/nonexistant', 'default')
    self.assertEqual(line, 'default')


if __name__ == '__main__':
  unittest.main()

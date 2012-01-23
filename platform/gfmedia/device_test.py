#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for device.py"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import fix_path

import dm_root
import sys
import device
import os
import shutil
import tempfile
import tornado.ioloop
import tornado.testing
import unittest

class DeviceGFMediaTest(tornado.testing.AsyncTestCase):
  """Tests for device.py."""

  def setUp(self):
    super(DeviceGFMediaTest, self).setUp()
    self.old_CONFIGDIR = device.CONFIGDIR
    self.old_GINSTALL = device.GINSTALL
    self.old_HNVRAM = device.HNVRAM
    self.old_REBOOT = device.REBOOT
    self.old_REPOMANIFEST = device.REPOMANIFEST
    self.old_VERSIONFILE = device.VERSIONFILE
    self.install_cb_called = False
    self.install_cb_faultcode = None
    self.install_cb_faultstring = None

  def tearDown(self):
    super(DeviceGFMediaTest, self).tearDown()
    device.CONFIGDIR = self.old_CONFIGDIR
    device.GINSTALL = self.old_GINSTALL
    device.HNVRAM = self.old_HNVRAM
    device.REBOOT = self.old_REBOOT
    device.REPOMANIFEST = self.old_REPOMANIFEST
    device.VERSIONFILE = self.old_VERSIONFILE

  def testGetSerialNumber(self):
    did = device.DeviceIdGFMedia()
    device.HNVRAM = "testdata/device/hnvramSN"
    self.assertEqual(did.SerialNumber, "123456789")

    device.HNVRAM = "testdata/device/hnvramFOO_Empty"
    self.assertEqual(did.SerialNumber, "000000000000")

    device.HNVRAM = "testdata/device/hnvramSN_Err"
    self.assertEqual(did.SerialNumber, "000000000000")

  def testBadHnvram(self):
    did = device.DeviceIdGFMedia()
    device.HNVRAM = "/no_such_binary_at_this_path"
    self.assertEqual(did.SerialNumber, "000000000000")

  def testModelName(self):
    did = device.DeviceIdGFMedia()
    device.HNVRAM = "testdata/device/hnvramPN"
    self.assertEqual(did.ModelName, "ModelName")

  def testSoftwareVersion(self):
    did = device.DeviceIdGFMedia()
    device.VERSIONFILE = "testdata/device/version"
    self.assertEqual(did.SoftwareVersion, "1.2.3")

  def testAdditionalSoftwareVersion(self):
    did = device.DeviceIdGFMedia()
    device.REPOMANIFEST = "testdata/device/repomanifest"
    self.assertEqual(did.AdditionalSoftwareVersion,
                     "platform 1111111111111111111111111111111111111111")

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


if __name__ == '__main__':
  unittest.main()

#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for device.py."""

__author__ = 'zixia@google.com (Ted Huang)'

# Modified based on gfmedia/device_media.py by Denton Gentry


import os
import shutil
import tempfile
import unittest

import google3
import tornado.ioloop
import tornado.testing
import device


class MockIoloop(object):
  def __init__(self):
    self.timeout = None
    self.callback = None

  def add_timeout(self, timeout, callback, monotonic=None):
    self.timeout = timeout
    self.callback = callback


class DeviceTest(tornado.testing.AsyncTestCase):
  """Tests for device.py."""

  def setUp(self):
    super(DeviceTest, self).setUp()
    self.old_CONFIGDIR = device.CONFIGDIR
    self.old_DOWNLOADDIR = device.DOWNLOADDIR
    self.old_GINSTALL = device.GINSTALL
    self.old_REBOOT = device.REBOOT
    self.old_MODELNAMEFILE = device.MODELNAMEFILE
    self.old_HWVERSIONFILE = device.HWVERSIONFILE
    self.old_SWVERSIONFILE = device.SWVERSIONFILE
    self.old_REPOMANIFEST = device.REPOMANIFEST
    self.install_cb_called = False
    self.install_cb_faultcode = None
    self.install_cb_faultstring = None

  def tearDown(self):
    super(DeviceTest, self).tearDown()
    device.CONFIGDIR = self.old_CONFIGDIR
    device.DOWNLOADDIR = self.old_DOWNLOADDIR
    device.GINSTALL = self.old_GINSTALL
    device.REBOOT = self.old_REBOOT
    device.MODELNAMEFILE = self.old_MODELNAMEFILE
    device.HWVERSIONFILE = self.old_HWVERSIONFILE
    device.SWVERSIONFILE = self.old_SWVERSIONFILE
    device.REPOMANIFEST = self.old_REPOMANIFEST

  def testGetSerialNumber(self):
    did = device.DeviceId()
    self.assertEqual(did.SerialNumber, '000000000000')

  def testModelName(self):
    did = device.DeviceId()
    device.MODELNAMEFILE = 'testdata/device/platform'
    self.assertEqual(did.ModelName, 'GFLT200')

    device.MODELNAMEFILE = 'testdata/device/platform_empty'
    self.assertEqual(did.ModelName, 'UnknownModel')

    device.MODELNAMEFILE = 'testdata/device/platform_err'
    self.assertEqual(did.ModelName, 'UnknownModel')

  def testSoftwareVersion(self):
    did = device.DeviceId()
    device.SWVERSIONFILE = 'testdata/device/version'
    self.assertEqual(did.SoftwareVersion, '1.2.3')

    device.SWVERSIONFILE = 'testdata/device/version_err'
    self.assertEqual(did.SoftwareVersion, '1.0')

  def testAdditionalSoftwareVersion(self):
    did = device.DeviceId()
    device.REPOMANIFEST = 'testdata/device/repomanifest'
    self.assertEqual(did.AdditionalSoftwareVersion,
                     'platform 1111111111111111111111111111111111111111')

    device.REPOMANIFEST = 'testdata/device/repomanifest_err'
    self.assertEqual(did.AdditionalSoftwareVersion, '0.0')

  def testGetHardwareVersion(self):
    did = device.DeviceId()
    device.HWVERSIONFILE = 'testdata/device/hw_ver'
    self.assertEqual(did.HardwareVersion, '1.3')

  def testAdditionalHardwareVersion(self):
    did = device.DeviceId()
    self.assertEqual(did.AdditionalHardwareVersion, '0.0')

  def install_callback(self, faultcode, faultstring, must_reboot):
    self.install_cb_called = True
    self.install_cb_faultcode = faultcode
    self.install_cb_faultstring = faultstring
    self.install_cb_must_reboot = must_reboot
    self.stop()

  def testBadInstaller(self):
    device.GINSTALL = '/dev/null'
    inst = device.Installer('/dev/null', ioloop=self.io_loop)
    inst.install(file_type='1 Firmware Upgrade Image',
                 target_filename='',
                 callback=self.install_callback)
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 9002)
    self.assertTrue(self.install_cb_faultstring)

  def testInstallerStdout(self):
    device.GINSTALL = 'testdata/device/installer_128k_stdout'
    inst = device.Installer('testdata/device/imagefile', ioloop=self.io_loop)
    inst.install(file_type='1 Firmware Upgrade Image',
                 target_filename='',
                 callback=self.install_callback)
    self.wait()
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 0)
    self.assertFalse(self.install_cb_faultstring)
    self.assertTrue(self.install_cb_must_reboot)

  def testInstallerFailed(self):
    device.GINSTALL = 'testdata/device/installer_fails'
    inst = device.Installer('testdata/device/imagefile', ioloop=self.io_loop)
    inst.install(file_type='1 Firmware Upgrade Image',
                 target_filename='',
                 callback=self.install_callback)
    self.wait()
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 9002)
    self.assertTrue(self.install_cb_faultstring)


if __name__ == '__main__':
  unittest.main()

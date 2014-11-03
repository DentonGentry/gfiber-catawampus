#!/usr/bin/python
# Copyright 2013 Google Inc. All Rights Reserved.
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
# pylint:disable=invalid-name
# pylint:disable=unused-argument

"""Unit tests for device.py."""

__author__ = 'zve@google.com (Alexei Zverovitch)'

import google3
import dm.periodic_statistics
import tornado.ioloop
import tornado.testing
from tr.wvtest import unittest
import device


class MockIoloop(object):

  def __init__(self):
    self.timeout = None
    self.callback = None

  # pylint:disable=unused-argument
  def add_timeout(self, timeout, callback, monotonic=None):
    self.timeout = timeout
    self.callback = callback


class DeviceTest(tornado.testing.AsyncTestCase, unittest.TestCase):
  """Tests for device.py."""

  def setUp(self):
    super(DeviceTest, self).setUp()
    self.old_ITERIFS = device.ITERIFS
    self.old_NVRAM = device.NVRAM
    self.install_cb_called = False
    self.install_cb_faultcode = None
    self.install_cb_faultstring = None
    device.ITERIFS = MockIterIfs

  def tearDown(self):
    super(DeviceTest, self).tearDown()
    device.NVRAM = self.old_NVRAM
    device.ITERIFS = self.old_ITERIFS

  def testValidateExports(self):
    device.NVRAM = 'testdata/device/nvram'
    did = device.DeviceId()
    periodic_stats = dm.periodic_statistics.PeriodicStatistics()
    dev = device.Device(did, periodic_stats)
    dev.ValidateExports()

  def testGetManufacturer(self):
    did = device.DeviceId()
    device.NVRAM = 'testdata/device/nvram'
    self.assertEqual(did.Manufacturer, 'ASUSTeK Computer Inc.')

    device.NVRAM = 'testdata/device/nvram_empty'
    self.assertEqual(did.Manufacturer, 'Unknown manufacturer')

    device.NVRAM = 'testdata/device/nvram_NOT_FOUND'
    self.assertEqual(did.Manufacturer, 'Unknown manufacturer')

  def testGetManufacturerOUI(self):
    did = device.DeviceId()
    self.assertEqual(did.ManufacturerOUI, 'F88FCA')

  def testGetModelName(self):
    did = device.DeviceId()
    device.NVRAM = 'testdata/device/nvram'
    self.assertEqual(did.ModelName, 'RT-N16')

    device.NVRAM = 'testdata/device/nvram_empty'
    self.assertEqual(did.ModelName, 'Unknown TomatoUSB device')

    device.NVRAM = 'testdata/device/nvram_NOT_FOUND'
    self.assertEqual(did.ModelName, 'Unknown TomatoUSB device')

  def testGetDescription(self):
    did = device.DeviceId()
    self.assertEqual(did.Description, 'TomatoUSB device')

  def testGetSerialNumber(self):
    did = device.DeviceId()
    device.NVRAM = 'testdata/device/nvram'
    self.assertEqual(did.SerialNumber, '12:34:56:78:9A:BC')

    device.NVRAM = 'testdata/device/nvram_empty'
    self.assertEqual(did.SerialNumber, '00:00:00:00:00:00')

    device.NVRAM = 'testdata/device/nvram_NOT_FOUND'
    self.assertEqual(did.SerialNumber, '00:00:00:00:00:00')

  def testGetHardwareVersion(self):
    did = device.DeviceId()
    device.NVRAM = 'testdata/device/nvram'
    self.assertEqual(did.HardwareVersion, 'RT-N16-00-07-01-00')

    device.NVRAM = 'testdata/device/nvram_empty'
    self.assertEqual(did.HardwareVersion, '')

    device.NVRAM = 'testdata/device/nvram_NOT_FOUND'
    self.assertEqual(did.HardwareVersion, '')

  def testGetAdditionalHardwareVersion(self):
    did = device.DeviceId()
    self.assertEqual(did.AdditionalHardwareVersion, '')

  def testGetSoftwareVersion(self):
    did = device.DeviceId()
    device.NVRAM = 'testdata/device/nvram'
    self.assertEqual(did.SoftwareVersion, '20130102030405')

    device.NVRAM = 'testdata/device/nvram_empty'
    self.assertEqual(did.SoftwareVersion, '')

    device.NVRAM = 'testdata/device/nvram_NOT_FOUND'
    self.assertEqual(did.SoftwareVersion, '')

  def testGetAdditionalSoftwareVersion(self):
    did = device.DeviceId()
    device.JFFS_VERSION_FILE = 'testdata/device/jffs-version.txt'
    self.assertEqual(did.AdditionalSoftwareVersion, '20130605040302')

    device.JFFS_VERSION_FILE = 'testdata/device_NOT_FOUND/jffs-version.txt'
    self.assertEqual(did.AdditionalSoftwareVersion, '')

    device.JFFS_VERSION_FILE = 'testdata/device/jffs-version.txt_NOT_FOUND'
    self.assertEqual(did.AdditionalSoftwareVersion, '')

    device.JFFS_VERSION_FILE = 'testdata/device/blank.txt'
    self.assertEqual(did.AdditionalSoftwareVersion, '')

  def testGetProductClass(self):
    did = device.DeviceId()
    device.NVRAM = 'testdata/device/nvram'
    self.assertEqual(did.ProductClass, 'RT-N16')

    device.NVRAM = 'testdata/device/nvram_empty'
    self.assertEqual(did.ProductClass, 'Generic_TomatoUSB')

    device.NVRAM = 'testdata/device/nvram_NOT_FOUND'
    self.assertEqual(did.ProductClass, 'Generic_TomatoUSB')

  def testGetModemFirmwareVersion(self):
    did = device.DeviceId()
    self.assertEqual(did.ModemFirmwareVersion, '')

  def install_callback(self, faultcode, faultstring, must_reboot):
    self.install_cb_called = True
    self.install_cb_faultcode = faultcode
    self.install_cb_faultstring = faultstring
    self.install_cb_must_reboot = must_reboot
    self.stop()

  def testBadFileType(self):
    device.INSTALL_FIRMWARE_IMAGE = 'testdata/device/install_firmware'
    device.INSTALL_JFFS_IMAGE = 'testdata/device/install_jffs'
    inst = device.Installer('/dev/null', ioloop=self.io_loop)
    inst.install(file_type='INVALID FILE TYPE',
                 target_filename='',
                 callback=self.install_callback)
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 9002)
    self.assertTrue(self.install_cb_faultstring)

  def testBadFirmwareInstaller(self):
    device.INSTALL_FIRMWARE_IMAGE = '/dev/null'
    device.INSTALL_JFFS_IMAGE = 'testdata/device/install_jffs'
    inst = device.Installer('/dev/null', ioloop=self.io_loop)
    inst.install(file_type=device.FILETYPE_FIRMWARE_IMAGE,
                 target_filename='',
                 callback=self.install_callback)
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 9002)
    self.assertTrue(self.install_cb_faultstring)

  def testBadJffsInstaller(self):
    device.INSTALL_FIRMWARE_IMAGE = 'testdata/device/install_firmware'
    device.INSTALL_JFFS_IMAGE = '/dev/null'
    inst = device.Installer('/dev/null', ioloop=self.io_loop)
    inst.install(file_type=device.FILETYPE_JFFS_IMAGE,
                 target_filename='',
                 callback=self.install_callback)
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 9002)
    self.assertTrue(self.install_cb_faultstring)

  def testFirmwareInstallerStdout(self):
    device.INSTALL_FIRMWARE_IMAGE = 'testdata/device/install_firmware'
    inst = device.Installer('testdata/device/firmware.trx', ioloop=self.io_loop)
    inst.install(file_type=device.FILETYPE_FIRMWARE_IMAGE,
                 target_filename='',
                 callback=self.install_callback)
    self.wait()
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 0)
    self.assertFalse(self.install_cb_faultstring)
    self.assertTrue(self.install_cb_must_reboot)

  def testJffsInstallerStdout(self):
    device.INSTALL_JFFS_IMAGE = 'testdata/device/install_jffs'
    inst = device.Installer('testdata/device/jffs.tgz', ioloop=self.io_loop)
    inst.install(file_type=device.FILETYPE_JFFS_IMAGE,
                 target_filename='',
                 callback=self.install_callback)
    self.wait()
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 0)
    self.assertFalse(self.install_cb_faultstring)
    self.assertTrue(self.install_cb_must_reboot)

  def testFirmwareInstallerFailed(self):
    device.INSTALL_FIRMWARE_IMAGE = 'testdata/device/install_fails'
    inst = device.Installer('testdata/device/firmware.trx', ioloop=self.io_loop)
    inst.install(file_type=device.FILETYPE_FIRMWARE_IMAGE,
                 target_filename='',
                 callback=self.install_callback)
    self.wait()
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 9002)
    self.assertTrue(self.install_cb_faultstring)

  def testJffsInstallerFailed(self):
    device.INSTALL_JFFS_IMAGE = 'testdata/device/install_fails'
    inst = device.Installer('testdata/device/jffs.trx', ioloop=self.io_loop)
    inst.install(file_type=device.FILETYPE_JFFS_IMAGE,
                 target_filename='',
                 callback=self.install_callback)
    self.wait()
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 9002)
    self.assertTrue(self.install_cb_faultstring)


def MockIterIfs(arg):
  """Mock out pynetlinux.Interface.Iterifs, return no interfaces."""
  return []


if __name__ == '__main__':
  unittest.main()

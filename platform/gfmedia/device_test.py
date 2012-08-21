#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
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

__author__ = 'dgentry@google.com (Denton Gentry)'

import unittest

import google3
import tornado.ioloop
import tornado.testing
import device


class DeviceTest(tornado.testing.AsyncTestCase):
  """Tests for device.py."""

  def setUp(self):
    super(DeviceTest, self).setUp()
    self.old_CONFIGDIR = device.CONFIGDIR
    self.old_GINSTALL = device.GINSTALL
    self.old_HNVRAM = device.HNVRAM
    self.old_PROC_CPUINFO = device.PROC_CPUINFO
    self.old_REBOOT = device.REBOOT
    self.old_REPOMANIFEST = device.REPOMANIFEST
    self.old_SET_ACS = device.SET_ACS
    self.old_VERSIONFILE = device.VERSIONFILE
    self.install_cb_called = False
    self.install_cb_faultcode = None
    self.install_cb_faultstring = None

  def tearDown(self):
    super(DeviceTest, self).tearDown()
    device.CONFIGDIR = self.old_CONFIGDIR
    device.GINSTALL = self.old_GINSTALL
    device.HNVRAM = self.old_HNVRAM
    device.PROC_CPUINFO = self.old_PROC_CPUINFO
    device.REBOOT = self.old_REBOOT
    device.REPOMANIFEST = self.old_REPOMANIFEST
    device.SET_ACS = self.old_SET_ACS
    device.VERSIONFILE = self.old_VERSIONFILE

  def testGetSerialNumber(self):
    did = device.DeviceId()
    device.HNVRAM = 'testdata/device/hnvramSN'
    self.assertEqual(did.SerialNumber, '123456789')

    device.HNVRAM = 'testdata/device/hnvramFOO_Empty'
    self.assertEqual(did.SerialNumber, '000000000000')

    device.HNVRAM = 'testdata/device/hnvramSN_Err'
    self.assertEqual(did.SerialNumber, '000000000000')

  def testBadHnvram(self):
    did = device.DeviceId()
    device.HNVRAM = '/no_such_binary_at_this_path'
    self.assertEqual(did.SerialNumber, '000000000000')

  def testModelName(self):
    did = device.DeviceId()
    device.HNVRAM = 'testdata/device/hnvramPN'
    self.assertEqual(did.ModelName, 'ModelName')

  def testSoftwareVersion(self):
    did = device.DeviceId()
    device.VERSIONFILE = 'testdata/device/version'
    self.assertEqual(did.SoftwareVersion, '1.2.3')

  def testAdditionalSoftwareVersion(self):
    did = device.DeviceId()
    device.REPOMANIFEST = 'testdata/device/repomanifest'
    self.assertEqual(did.AdditionalSoftwareVersion,
                     'platform 1111111111111111111111111111111111111111')

  def testGetHardwareVersion(self):
    device.PROC_CPUINFO = 'testdata/proc_cpuinfo'
    did = device.DeviceId()
    self.assertEqual(did.HardwareVersion, 'BCM7425B2')

  def testFanSpeed(self):
    fan = device.FanReadGpio(filename='testdata/fanspeed')
    self.assertEqual(fan.RPM, 1800)

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

  def testSetAcs(self):
    device.SET_ACS = 'testdata/device/set-acs'
    pc = device.PlatformConfig()
    self.assertEqual(pc.GetAcsUrl(), 'bar')
    # just check that this does not raise an AttributeError
    pc.SetAcsUrl('foo')


if __name__ == '__main__':
  unittest.main()

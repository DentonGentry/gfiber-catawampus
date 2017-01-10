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
# pylint:disable=invalid-name
# pylint:disable=unused-argument

"""Unit tests for device.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
import device
import tornado.ioloop
import tornado.testing
import tr.handle
import tr.session
from tr.wvtest import unittest


class MockIoloop(object):

  def __init__(self):
    self.timeout = None
    self.callback = None

  def add_timeout(self, timeout, callback, monotonic=None):
    self.timeout = timeout
    self.callback = callback


class DeviceTest(tornado.testing.AsyncTestCase, unittest.TestCase):
  """Tests for device.py."""

  def setUp(self):
    super(DeviceTest, self).setUp()
    self.old_ACTIVEWAN = device.ACTIVEWAN
    self.old_CONFIGDIR = device.CONFIGDIR
    self.old_GINSTALL = device.GINSTALL
    self.old_HNVRAM = device.HNVRAM
    self.old_ISNETWORKBOX = device.ISNETWORKBOX
    self.old_LEDSTATUS = device.LEDSTATUS
    self.old_NAND_MB = device.NAND_MB
    self.old_PROC_CPUINFO = device.PROC_CPUINFO
    self.old_PYNETIFCONF = device.PYNETIFCONF
    self.old_REBOOT = device.REBOOT
    self.old_REPOMANIFEST = device.REPOMANIFEST
    self.old_VERSIONFILE = device.VERSIONFILE
    device.ACTIVEWAN = 'testdata/device/activewan'
    device.PYNETIFCONF = MockPynetInterface
    self.install_cb_called = False
    self.install_cb_faultcode = None
    self.install_cb_faultstring = None
    tr.session.cache.flush()

  def tearDown(self):
    super(DeviceTest, self).tearDown()
    device.ACTIVEWAN = self.old_ACTIVEWAN
    device.CONFIGDIR = self.old_CONFIGDIR
    device.GINSTALL = self.old_GINSTALL
    device.HNVRAM = self.old_HNVRAM
    device.ISNETWORKBOX = self.old_ISNETWORKBOX
    device.LEDSTATUS = self.old_LEDSTATUS
    device.NAND_MB = self.old_NAND_MB
    device.PROC_CPUINFO = self.old_PROC_CPUINFO
    device.PYNETIFCONF = self.old_PYNETIFCONF
    device.REBOOT = self.old_REBOOT
    device.REPOMANIFEST = self.old_REPOMANIFEST
    device.VERSIONFILE = self.old_VERSIONFILE

  def testGetSerialNumber(self):
    device.HNVRAM = 'testdata/device/hnvram'
    did = device.DeviceId()
    self.assertEqual(did.SerialNumber, '123456789')

    device.HNVRAM = 'testdata/device/hnvramSN_Empty'
    did = device.DeviceId()
    self.assertEqual(did.SerialNumber, '000000000000')

    device.HNVRAM = 'testdata/device/hnvramSN_Err'
    did = device.DeviceId()
    self.assertEqual(did.SerialNumber, '000000000000')

  def testBadHnvram(self):
    device.HNVRAM = '/no_such_binary_at_this_path'
    did = device.DeviceId()
    self.assertEqual(did.SerialNumber, '000000000000')

  def testModelName(self):
    device.HNVRAM = 'testdata/device/hnvram'
    did = device.DeviceId()
    self.assertEqual(did.ModelName, 'ModelName')

  def testSoftwareVersion(self):
    device.VERSIONFILE = 'testdata/device/version'
    did = device.DeviceId()
    self.assertEqual(did.SoftwareVersion, '1.2.3')

  def testAdditionalSoftwareVersion(self):
    device.REPOMANIFEST = 'testdata/device/repomanifest'
    did = device.DeviceId()
    self.assertEqual(did.AdditionalSoftwareVersion,
                     'platform 1111111111111111111111111111111111111111')

  def testGetHardwareVersion(self):
    device.HNVRAM = 'testdata/device/hnvram'
    device.PROC_CPUINFO = 'testdata/device/proc_cpuinfo_b0'
    device.NAND_MB = 'testdata/device/nand_size_mb_rev1'
    did = device.DeviceId()
    self.assertEqual(did.HardwareVersion, 'ver')

    device.HNVRAM = 'testdata/device/hnvramFOO_Empty'
    did = device.DeviceId()
    self.assertEqual(did.HardwareVersion, '0')

    device.PROC_CPUINFO = 'testdata/device/proc_cpuinfo_b2'
    did = device.DeviceId()
    self.assertEqual(did.HardwareVersion, '1')

    device.NAND_MB = 'testdata/device/nand_size_mb_rev2'
    did = device.DeviceId()
    self.assertEqual(did.HardwareVersion, '2')

    device.NAND_MB = 'testdata/device/nand_size_mb_unk'
    did = device.DeviceId()
    self.assertEqual(did.HardwareVersion, '0')

  def testFanSpeed(self):
    fan = device.FanReadGpio(speed_filename='testdata/fanspeed',
                             percent_filename='testdata/fanpercent')
    tr.handle.ValidateExports(fan)
    self.assertEqual(fan.RPM, 3600)
    self.assertEqual(fan.DesiredPercentage, 50)
    fan = device.FanReadGpio(speed_filename='foo',
                             percent_filename='bar')
    self.assertEqual(fan.RPM, -1)
    self.assertEqual(fan.DesiredPercentage, -1)

  def install_callback(self, faultcode, faultstring, must_reboot):
    self.install_cb_called = True
    self.install_cb_faultcode = faultcode
    self.install_cb_faultstring = faultstring
    self.install_cb_must_reboot = must_reboot
    self.stop()

  def testBadInstaller(self):
    device.GINSTALL = '/dev/null'
    inst = device.Installer('/dev/null', ioloop=self.io_loop)
    inst.Install(file_type='1 Firmware Upgrade Image',
                 target_filename='',
                 callback=self.install_callback)
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 9002)
    self.assertTrue(self.install_cb_faultstring)

  def testInstallerStdout(self):
    device.GINSTALL = 'testdata/device/installer_128k_stdout'
    inst = device.Installer('testdata/device/imagefile', ioloop=self.io_loop)
    inst.Install(file_type='1 Firmware Upgrade Image',
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
    inst.Install(file_type='1 Firmware Upgrade Image',
                 target_filename='',
                 callback=self.install_callback)
    self.wait()
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 9002)
    self.assertTrue(self.install_cb_faultstring)

  def testValidateExports(self):
    tr.handle.ValidateExports(device.LANDevice('', 'br0'))
    tr.handle.ValidateExports(device.LANDevice('portal', ''))
    tr.handle.ValidateExports(device.Ethernet())
    # TODO(apenwarr): instantiate the entire schema here for proper testing.
    #   It's a pain because many subsections may need fake data.

  def testActiveWan(self):
    device.ACTIVEWAN = 'testdata/device/activewan'
    self.assertEqual(device.activewan('foo0'), '')
    self.assertEqual(device.activewan('bar0'), 'Down')
    device.ACTIVEWAN = 'testdata/device/activewan_fail'
    self.assertEqual(device.activewan('foo0'), '')
    self.assertEqual(device.activewan('bar0'), '')
    device.ACTIVEWAN = 'testdata/device/activewan_empty'
    self.assertEqual(device.activewan('foo0'), '')
    self.assertEqual(device.activewan('bar0'), '')


class MockPynetInterface(object):

  def __init__(self, ifname):
    self.ifname = ifname

  def get_index(self):
    raise IOError('No such interface in test')


if __name__ == '__main__':
  unittest.main()

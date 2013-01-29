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
    self.old_ACSCONNECTED = device.ACSCONNECTED
    self.old_CONFIGDIR = device.CONFIGDIR
    self.old_DOWNLOADDIR = device.DOWNLOADDIR
    self.old_GINSTALL = device.GINSTALL
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
    device.ACSCONNECTED = self.old_ACSCONNECTED
    device.CONFIGDIR = self.old_CONFIGDIR
    device.DOWNLOADDIR = self.old_DOWNLOADDIR
    device.GINSTALL = self.old_GINSTALL
    device.PROC_CPUINFO = self.old_PROC_CPUINFO
    device.REBOOT = self.old_REBOOT
    device.REPOMANIFEST = self.old_REPOMANIFEST
    device.SET_ACS = self.old_SET_ACS
    device.VERSIONFILE = self.old_VERSIONFILE

  def testGetSerialNumber(self):
    did = device.DeviceId()
    self.assertEqual(did.SerialNumber, '666666666666')

  def testModelName(self):
    did = device.DeviceId()
    self.assertEqual(did.ModelName, 'GFONU')

  def testSoftwareVersion(self):
    did = device.DeviceId()
    self.assertEqual(did.SoftwareVersion, '1.0')

  def testAdditionalSoftwareVersion(self):
    did = device.DeviceId()
    self.assertEqual(did.AdditionalSoftwareVersion, '1.0')

  # TODO: (zixia) change based on real hardware chipset
  def testGetHardwareVersion(self):
    device.PROC_CPUINFO = 'testdata/device/proc_cpuinfo'
    did = device.DeviceId()
    self.assertEqual(did.HardwareVersion, '1.0')

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
    #TODO(zixia): leave for GINSTALL
    #self.assertEqual(self.install_cb_faultcode, 0)
    #self.assertFalse(self.install_cb_faultstring)
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
    scriptout = tempfile.NamedTemporaryFile()
    os.environ['TESTOUTPUT'] = scriptout.name
    pc = device.PlatformConfig(ioloop=MockIoloop())
    self.assertEqual(pc.GetAcsUrl(), 'bar')
    pc.SetAcsUrl('foo')
    self.assertEqual(scriptout.read().strip(), 'cwmp foo')

  def testClearAcs(self):
    device.SET_ACS = 'testdata/device/set-acs'
    scriptout = tempfile.NamedTemporaryFile()
    os.environ['TESTOUTPUT'] = scriptout.name
    pc = device.PlatformConfig(ioloop=MockIoloop())
    pc.SetAcsUrl('')
    self.assertEqual(scriptout.read().strip(), 'cwmp clear')

  def testAcsAccess(self):
    device.SET_ACS = 'testdata/device/set-acs'
    scriptout = tempfile.NamedTemporaryFile()
    os.environ['TESTOUTPUT'] = scriptout.name
    ioloop = MockIoloop()
    tmpdir = tempfile.mkdtemp()
    tmpfile = os.path.join(tmpdir, 'acsconnected')
    self.assertRaises(OSError, os.stat, tmpfile)  # File does not exist yet
    device.ACSCONNECTED = tmpfile
    pc = device.PlatformConfig(ioloop)
    acsurl = 'this is the acs url'

    # Simulate ACS connection
    pc.AcsAccessAttempt(acsurl)
    pc.AcsAccessSuccess(acsurl)
    self.assertTrue(os.stat(tmpfile))
    self.assertEqual(open(tmpfile, 'r').read(), acsurl)
    self.assertTrue(ioloop.timeout)
    self.assertTrue(ioloop.callback)

    # Simulate timeout
    pc.AcsAccessAttempt(acsurl)
    scriptout.truncate()
    ioloop.callback()
    self.assertRaises(OSError, os.stat, tmpfile)
    self.assertEqual(scriptout.read().strip(), 'timeout ' + acsurl)

    # cleanup
    shutil.rmtree(tmpdir)


if __name__ == '__main__':
  unittest.main()

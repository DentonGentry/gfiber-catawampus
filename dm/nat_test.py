#!/usr/bin/python
# Copyright 2014 Google Inc. All Rights Reserved.
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
# pylint: disable-msg=C6409

"""Unit tests for nat.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import tempfile
import unittest

import google3
import nat
import tr.mainloop


class NatTest(unittest.TestCase):
  def setUp(self):
    super(NatTest, self).setUp()
    self.tmpdir = tempfile.mkdtemp()
    self.loop = tr.mainloop.MainLoop()
    self.old_RESTARTCMD = nat.RESTARTCMD
    self.restartfile = os.path.join(self.tmpdir, 'restarted')
    nat.RESTARTCMD = ['testdata/nat/restart', self.restartfile]

  def tearDown(self):
    super(NatTest, self).tearDown()
    shutil.rmtree(self.tmpdir)
    nat.RESTARTCMD = self.old_RESTARTCMD

  def testValidateExports(self):
    n = nat.NAT(dmroot=None)
    n.ValidateExports()
    p = n.PortMapping()
    p.ValidateExports()

  def testLeaseDuration(self):
    """A non-zero LeaseDuration is not supported."""
    p = nat.NAT(dmroot=None).PortMapping()
    p.LeaseDuration = 0  # should succeed
    self.assertRaises(ValueError, setattr, p, 'LeaseDuration', 1)

  def testStatus(self):
    dmroot = DeviceModelRoot()
    n = nat.NAT(dmroot=dmroot)
    p = n.PortMapping()
    self.assertEqual(p.Status, 'Disabled')
    p.Enable = True
    self.assertEqual(p.Status, 'Error_Misconfigured')
    p.InternalClient = '1.1.1.1'
    self.assertEqual(p.Status, 'Error_Misconfigured')
    p.InternalPort = 80
    self.assertEqual(p.Status, 'Error_Misconfigured')
    p.Interface = 'Device.IP.Interface.1'
    self.assertEqual(p.Status, 'Error_Misconfigured')
    p.Protocol = 'TCP'
    self.assertEqual(p.Status, 'Enabled')

  def testInterface(self):
    dmroot = DeviceModelRoot()
    n = nat.NAT(dmroot=dmroot)
    p = n.PortMapping()
    p.Interface = 'Device.IP.Interface.1'  # should succeed
    self.assertEqual(p.Interface, 'Device.IP.Interface.1')
    del dmroot.Device.IP.InterfaceList['1']
    self.assertEqual(p.Interface, '')
    self.assertRaises(ValueError, setattr, p, 'Interface',
                      'Device.IP.Interface.2')


class DeviceModelRoot(tr.core.Exporter):
  def __init__(self):
    super(DeviceModelRoot, self).__init__()
    self.Device = Device()
    self.Export(['Device'])


class Device(tr.core.Exporter):
  def __init__(self):
    super(Device, self).__init__()
    self.IP = IP()
    self.Export(['IP'])


class IP(tr.core.Exporter):
  def __init__(self):
    super(IP, self).__init__()
    o = object()
    self.InterfaceList = {'1': o}
    self.Export(lists=['Interface'])


if __name__ == '__main__':
  unittest.main()

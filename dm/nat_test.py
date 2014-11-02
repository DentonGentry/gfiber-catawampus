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
# pylint:disable=invalid-name

"""Unit tests for nat.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import tempfile
import google3
from tr.wvtest import unittest
import nat
import tr.mainloop


class NatTest(unittest.TestCase):
  def setUp(self):
    super(NatTest, self).setUp()
    self.tmpdir = tempfile.mkdtemp()
    self.loop = tr.mainloop.MainLoop()
    self.old_OUTPUTFILE4 = nat.OUTPUTFILE4
    self.old_OUTPUTFILE6 = nat.OUTPUTFILE6
    self.old_RESTARTCMD = nat.RESTARTCMD
    self.old_DMZFILE4 = nat.DMZFILE4
    self.old_DMZFILE6 = nat.DMZFILE6
    self.restartfile = os.path.join(self.tmpdir, 'restarted')
    self.outputfile4 = os.path.join(self.tmpdir, 'config4')
    self.outputfile6 = os.path.join(self.tmpdir, 'config6')
    self.dmzfile4 = os.path.join(self.tmpdir, 'dmz4')
    self.dmzfile6 = os.path.join(self.tmpdir, 'dmz6')
    nat.DMZFILE4 = self.dmzfile4
    nat.DMZFILE6 = self.dmzfile6
    nat.OUTPUTFILE4 = self.outputfile4
    nat.OUTPUTFILE6 = self.outputfile6
    nat.RESTARTCMD = ['testdata/nat/restart', self.restartfile]

  def tearDown(self):
    super(NatTest, self).tearDown()
    shutil.rmtree(self.tmpdir)
    nat.DMZFILE4 = self.old_DMZFILE4
    nat.DMZFILE6 = self.old_DMZFILE6
    nat.OUTPUTFILE4 = self.old_OUTPUTFILE4
    nat.OUTPUTFILE6 = self.old_OUTPUTFILE6
    nat.RESTARTCMD = self.old_RESTARTCMD

  def testValidateExports(self):
    n = nat.NAT(dmroot=DeviceModelRoot())
    n.ValidateExports()
    p = n.PortMapping()
    p.ValidateExports()

  def testLeaseDuration(self):
    """A non-zero LeaseDuration is not supported."""
    n = nat.NAT(dmroot=DeviceModelRoot())
    p = n.PortMapping()
    p.LeaseDuration = 0  # should succeed
    self.assertRaises(ValueError, setattr, p, 'LeaseDuration', 1)

  def testStatus(self):
    n = nat.NAT(dmroot=DeviceModelRoot())
    p = n.PortMapping()
    p.Enable = False
    self.assertEqual(p.Status, 'Disabled')
    p.Enable = True
    self.assertEqual(p.Status, 'Error_Misconfigured')
    p.Protocol = 'TCP'
    self.assertEqual(p.Status, 'Error_Misconfigured')
    p.InternalPort = 80
    self.assertEqual(p.Status, 'Error_Misconfigured')
    p.Interface = 'Device.IP.Interface.1'
    self.assertEqual(p.Status, 'Error_Misconfigured')
    p.InternalClient = '1.1.1.1'
    self.assertEqual(p.Status, 'Enabled')

  def testInterface(self):
    dmroot = DeviceModelRoot()
    n = nat.NAT(dmroot=dmroot)
    p = n.PortMapping()
    p.Interface = 'Device.IP.Interface.1'  # should succeed
    self.assertEqual(p.Interface, 'Device.IP.Interface.1')
    del dmroot.Device.IP.InterfaceList['1']
    self.assertEqual(p.Interface, '')
    # No such interface
    self.assertRaises(ValueError, setattr, p, 'Interface',
                      'Device.IP.Interface.2')

  def testPortMappingPrecedence(self):
    n = nat.NAT(dmroot=DeviceModelRoot())
    p = n.PortMapping()
    self.assertEqual(p.Precedence(), 4)
    p.ExternalPort = 1
    self.assertEqual(p.Precedence(), 3)
    p.RemoteHost = '1.2.3.4'
    p.ExternalPort = 0
    self.assertEqual(p.Precedence(), 2)
    p.ExternalPort = 1
    self.assertEqual(p.Precedence(), 1)

  def testDescriptionTooLong(self):
    """Description is stored in kernel ipt_comment. Must be short."""
    n = nat.NAT(dmroot=DeviceModelRoot())
    p = n.PortMapping()
    p.Description = 'A' * 256  # should succeed
    self.assertRaises(ValueError, setattr, p, 'Description', 'A' * 257)

  def testConfigWrite(self):
    n = nat.NAT(dmroot=DeviceModelRoot())
    p = n.PortMapping()
    p.AllInterfaces = True
    p.Description = 'Description'
    p.Enable = True
    p.InternalClient = '1.1.1.1'
    p.InternalPort = 80
    p.Protocol = 'TCP'
    n.PortMappingList['1'] = p

    p = n.PortMapping()
    p.Enable = True
    p.ExternalPort = 1
    p.ExternalPortEndRange = 9
    p.InternalClient = '3.3.3.3'
    p.InternalPort = 90
    p.Interface = 'Device.IP.Interface.1'
    p.Protocol = 'UDP'
    p.RemoteHost = '2.2.2.2'
    n.PortMappingList['2'] = p

    self.loop.RunOnce(timeout=1)
    config4 = open(self.outputfile4).read()
    expected = ['CWMP_1_COMMENT=IDX_2:', 'CWMP_1_PROTOCOL=UDP',
                'CWMP_1_SOURCE=2.2.2.2', 'CWMP_1_GATEWAY=9.9.9.9',
                'CWMP_1_DEST=3.3.3.3', 'CWMP_1_SPORT=1:9', 'CWMP_1_DPORT=90',
                'CWMP_1_ENABLE=1',
                'CWMP_2_COMMENT=IDX_1:4465736372697074696f6e',
                'CWMP_2_PROTOCOL=TCP', 'CWMP_2_SOURCE=0/0',
                'CWMP_2_GATEWAY=0/0', 'CWMP_2_DEST=1.1.1.1', 'CWMP_2_SPORT=0',
                'CWMP_2_DPORT=80', 'CWMP_2_ENABLE=1']
    for line in config4.splitlines():
      line = line.strip()
      if line and not line.startswith('#'):
        self.assertTrue(line in expected)
        expected.remove(line)
    self.assertEqual(len(expected), 0)
    config6 = open(self.outputfile6).read()
    self.assertEqual(config6, '')
    self.assertTrue(os.path.exists(self.restartfile))

  def testConfigWriteIP6(self):
    n = nat.NAT(dmroot=DeviceModelRoot())
    p = n.PortMapping()
    p.AllInterfaces = True
    p.Enable = True
    p.InternalClient = 'fe80::fa8f:caff:fe11:1111'
    p.InternalPort = 80
    p.Protocol = 'TCP'
    n.PortMappingList['1'] = p

    self.loop.RunOnce(timeout=1)
    config4 = open(self.outputfile4).read()
    self.assertEqual(config4, '')
    config6 = open(self.outputfile6).read()
    expected = ['CWMP_1_COMMENT=IDX_1:', 'CWMP_1_PROTOCOL=TCP',
                'CWMP_1_SOURCE=::/0', 'CWMP_1_GATEWAY=::/0',
                'CWMP_1_DEST=fe80::fa8f:caff:fe11:1111',
                'CWMP_1_SPORT=0', 'CWMP_1_DPORT=80', 'CWMP_1_ENABLE=1']
    for line in config6.splitlines():
      line = line.strip()
      if line and not line.startswith('#'):
        self.assertTrue(line in expected)
        expected.remove(line)
    self.assertEqual(len(expected), 0)
    self.assertTrue(os.path.exists(self.restartfile))

  def testConfigIncomplete(self):
    n = nat.NAT(dmroot=DeviceModelRoot())
    p = n.PortMapping()
    n.PortMappingList['1'] = p
    self.loop.RunOnce(timeout=1)
    self.assertFalse(os.path.exists(self.outputfile4))
    self.assertFalse(os.path.exists(self.outputfile6))

    p.AllInterfaces = True
    p.Description = 'Description'
    self.loop.RunOnce(timeout=1)
    self.assertFalse(os.stat(self.outputfile4).st_size)
    self.assertFalse(os.stat(self.outputfile6).st_size)

    p.InternalClient = '1.1.1.1'
    p.InternalPort = 80
    p.Protocol = 'TCP'
    self.loop.RunOnce(timeout=1)
    self.assertFalse(os.stat(self.outputfile4).st_size)
    self.assertFalse(os.stat(self.outputfile6).st_size)

    p.Enable = True
    self.loop.RunOnce(timeout=1)
    self.assertTrue(os.stat(self.outputfile4).st_size)
    self.assertFalse(os.stat(self.outputfile6).st_size)

  def testConfigWritePortRangeSize(self):
    n = nat.NAT(dmroot=DeviceModelRoot())
    p = n.PortMapping()
    p.Enable = True
    p.ExternalPort = 1
    p.X_CATAWAMPUS_ORG_PortRangeSize = 100
    p.InternalClient = '4.4.4.4'
    p.InternalPort = 90
    p.Interface = 'Device.IP.Interface.1'
    p.Protocol = 'UDP'
    p.RemoteHost = '5.5.5.5'
    n.PortMappingList['1'] = p

    p = n.PortMapping()
    p.Enable = True
    p.ExternalPort = 10
    p.X_CATAWAMPUS_ORG_PortRangeSize = 51
    p.InternalClient = 'fe80::fa8f:caff:fe11:1111'
    p.InternalPort = 91
    p.Interface = 'Device.IP.Interface.1'
    p.Protocol = 'TCP'
    n.PortMappingList['2'] = p

    self.loop.RunOnce(timeout=1)
    config4 = open(self.outputfile4).read()
    expected = ['CWMP_1_COMMENT=IDX_1:', 'CWMP_1_PROTOCOL=UDP',
                'CWMP_1_SOURCE=5.5.5.5', 'CWMP_1_GATEWAY=9.9.9.9',
                'CWMP_1_DEST=4.4.4.4', 'CWMP_1_SPORT=1:100',
                'CWMP_1_DPORT=90:189', 'CWMP_1_ENABLE=1']
    for line in config4.splitlines():
      line = line.strip()
      if line and not line.startswith('#'):
        self.assertTrue(line in expected)
        expected.remove(line)
    self.assertEqual(len(expected), 0)

    config6 = open(self.outputfile6).read()
    expected = ['CWMP_2_COMMENT=IDX_2:', 'CWMP_2_PROTOCOL=TCP',
                'CWMP_2_SOURCE=::/0', 'CWMP_2_GATEWAY=1000::0001',
                'CWMP_2_DEST=fe80::fa8f:caff:fe11:1111',
                'CWMP_2_SPORT=10:60', 'CWMP_2_DPORT=91:141', 'CWMP_2_ENABLE=1']
    for line in config6.splitlines():
      line = line.strip()
      if line and not line.startswith('#'):
        self.assertTrue(line in expected)
        expected.remove(line)
    self.assertEqual(len(expected), 0)
    self.assertTrue(os.path.exists(self.restartfile))

  def testConfigDeleteObject(self):
    n = nat.NAT(dmroot=DeviceModelRoot())
    p = n.PortMapping()
    p.AllInterfaces = True
    p.Enable = True
    p.InternalClient = '1.1.1.1'
    p.InternalPort = 80
    p.Protocol = 'TCP'
    n.PortMappingList['1'] = p
    self.loop.RunOnce(timeout=1)
    n.DeleteExportObject('PortMapping', '1')
    self.loop.RunOnce(timeout=1)

    config = open(self.outputfile4).read()
    self.assertFalse(config)

  def testRestartFails(self):
    print 'The following tracebacks are normal, they are part of the test.'
    nat.RESTARTCMD = ['testdata/nat/restart_fails']
    n = nat.NAT(dmroot=DeviceModelRoot())
    p = n.PortMapping()
    p.InternalClient = '1.1.1.1'
    p.Enable = True
    n.PortMappingList['1'] = p
    self.loop.RunOnce(timeout=1)
    self.assertTrue(os.path.exists(self.outputfile4))

  def testDmz4(self):
    n = nat.NAT(dmroot=DeviceModelRoot())
    p = n.PortMapping()
    n.PortMappingList['1'] = p
    p.InternalClient = '1.1.1.1'
    p.Enable = True
    self.assertFalse(os.path.exists(self.dmzfile4))
    self.loop.RunOnce(timeout=1)
    self.assertTrue(os.path.exists(self.dmzfile4))
    self.assertFalse(os.path.exists(self.dmzfile6))
    self.assertTrue(os.path.exists(self.outputfile4))
    config4 = open(self.outputfile4).read()
    self.assertFalse(config4)
    p.Enable = False
    self.loop.RunOnce(timeout=1)
    self.assertFalse(os.path.exists(self.dmzfile4))

  def testDmz6(self):
    n = nat.NAT(dmroot=DeviceModelRoot())
    p = n.PortMapping()
    n.PortMappingList['1'] = p
    p.InternalClient = 'fe80::fa8f:caff:fe11:1111'
    p.Enable = True
    self.assertFalse(os.path.exists(self.dmzfile6))
    self.loop.RunOnce(timeout=1)
    self.assertFalse(os.path.exists(self.dmzfile4))
    self.assertTrue(os.path.exists(self.dmzfile6))
    self.assertTrue(os.path.exists(self.outputfile6))
    config4 = open(self.outputfile4).read()
    self.assertFalse(config4)
    p.Enable = False
    self.loop.RunOnce(timeout=1)
    self.assertFalse(os.path.exists(self.dmzfile6))


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
    o = IPInterface()
    self.InterfaceList = {'1': o}
    self.Export(lists=['Interface'])


class IPInterface(tr.core.Exporter):
  def __init__(self):
    super(IPInterface, self).__init__()
    self.IPv4AddressList = {'1': IPv4Address()}
    self.IPv6AddressList = {'1': IPv6Address()}


class IPv4Address(tr.core.Exporter):
  def __init__(self):
    super(IPv4Address, self).__init__()
    self.IPAddress = '9.9.9.9'


class IPv6Address(tr.core.Exporter):
  def __init__(self):
    super(IPv6Address, self).__init__()
    self.IPAddress = '1000::0001'


if __name__ == '__main__':
  unittest.main()

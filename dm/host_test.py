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
# pylint: disable-msg=C6409

"""Unit tests for host.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import unittest

import google3
import platform.fakecpe.device
import tr.tr098_v1_4
import host


def TimeNow():
  return 1384057000.0


class TestDeviceModelRoot(tr.core.Exporter):
  def __init__(self, tr98=None, tr181=None):
    super(TestDeviceModelRoot, self).__init__()
    if tr98:
      self.InternetGatewayDevice = tr98
      self.Export(['InternetGatewayDevice'])
    if tr181:
      self.Device = tr181
      self.Export(['Device'])


class HostTest(unittest.TestCase):
  def setUp(self):
    self.old_DHCP_FINGERPRINTS = host.DHCP_FINGERPRINTS
    self.old_PROC_NET_ARP = host.PROC_NET_ARP
    self.old_SYS_CLASS_NET_PATH = host.SYS_CLASS_NET_PATH
    host.DHCP_FINGERPRINTS = 'testdata/host/fingerprints-dhcp'
    host.PROC_NET_ARP = '/dev/null'
    host.SYS_CLASS_NET_PATH = 'testdata/host/sys/class/net'
    self.old_TIMENOW = host.TIMENOW
    host.TIMENOW = TimeNow

  def tearDown(self):
    host.SYS_CLASS_NET_PATH = self.old_SYS_CLASS_NET_PATH
    host.TIMENOW = self.old_TIMENOW

  def testValidateExports(self):
    hosts = host.Hosts()
    hosts.ValidateExports()
    h = host.Host()
    h.ValidateExports()

  def testHostFields(self):
    h = host.Host(PhysAddress='mac',
                  ip4=['ip4_1', 'ip4_2', 'ip4_3'],
                  ip6=['ip6_1', 'ip6_2', 'ip6_3', 'ip6_4'],
                  DHCPClient='dhcpclient',
                  AssociatedDevice='associated_device',
                  Layer1Interface='l1iface', Layer3Interface='l3iface',
                  HostName='hostname', LeaseTimeRemaining=1000,
                  VendorClassID='vendor_class_id',
                  ClientID='client_id', UserClassID='user_class_id')
    h.ValidateExports()
    self.assertEqual(h.AssociatedDevice, 'associated_device')
    self.assertEqual(h.ClientID, 'client_id')
    self.assertEqual(h.DHCPClient, 'dhcpclient')
    self.assertEqual(h.HostName, 'hostname')
    self.assertEqual(h.Layer1Interface, 'l1iface')
    self.assertEqual(h.Layer3Interface, 'l3iface')
    self.assertEqual(h.LeaseTimeRemaining, 1000)
    self.assertEqual(h.PhysAddress, 'mac')
    self.assertEqual(h.UserClassID, 'user_class_id')
    self.assertEqual(h.VendorClassID, 'vendor_class_id')
    self.assertEqual(len(h.IPv4AddressList), 3)
    self.assertEqual(h.IPv4AddressList['1'].IPAddress, 'ip4_1')
    self.assertEqual(h.IPv4AddressList['2'].IPAddress, 'ip4_2')
    self.assertEqual(h.IPv4AddressList['3'].IPAddress, 'ip4_3')
    h.IPv4AddressList['1'].ValidateExports()
    h.IPv4AddressList['2'].ValidateExports()
    h.IPv4AddressList['3'].ValidateExports()
    self.assertEqual(len(h.IPv6AddressList), 4)
    self.assertEqual(h.IPv6AddressList['1'].IPAddress, 'ip6_1')
    h.IPv6AddressList['1'].ValidateExports()
    h.IPv6AddressList['2'].ValidateExports()
    h.IPv6AddressList['3'].ValidateExports()
    h.IPv6AddressList['4'].ValidateExports()
    self.assertEqual(h.IPv6AddressList['2'].IPAddress, 'ip6_2')
    self.assertEqual(h.IPv6AddressList['3'].IPAddress, 'ip6_3')
    self.assertEqual(h.IPv6AddressList['4'].IPAddress, 'ip6_4')

  def testHostsFromBridge(self):
    iflookup = {'eth0': 'Ethernet', 'eth1.0': 'MoCA',}
    h = host.Hosts(iflookup, bridgename='br0')
    self.assertEqual(len(h.HostList), 10)
    h.ValidateExports()
    # brforward file taken from a real system in the lab
    expected = {
        'e8:39:35:b8:66:c8': 'Ethernet',
        '68:05:ca:16:2a:90': 'Ethernet',
        '28:c0:da:3a:b4:15': 'Ethernet',
        'f8:8f:ca:00:c4:47': 'MoCA',
        'f8:8f:ca:00:da:6c': 'Ethernet',
        'f8:8f:ca:09:4e:25': 'MoCA',
        'f8:8f:ca:00:c2:df': 'Ethernet',
        'f8:8f:ca:00:c2:47': 'Ethernet',
        '00:00:de:ad:be:ef': 'Ethernet',
        'ac:4b:c8:7e:32:04': 'Ethernet',
    }
    for entry in h.HostList.values():
      self.assertTrue(entry.PhysAddress in expected)
      self.assertEqual(entry.Layer1Interface, expected[entry.PhysAddress])
      del expected[entry.PhysAddress]
      entry.ValidateExports()
    self.assertEqual(len(expected), 0)

  def testMissingFdbFile(self):
    iflookup = {'eth0': 'Ethernet', 'eth1.0': 'MoCA',}
    h = host.Hosts(iflookup, bridgename='nonexistent0')
    self.assertEqual(len(h.HostList), 0)

  def testGetHostsFromArp(self):
    host.PROC_NET_ARP = 'testdata/host/proc_net_arp'
    iflookup = {'foo0': 'Device.Foo.Interface.1',
                'foo1': 'Device.Foo.Interface.2'}
    hosts = host.Hosts(iflookup)
    self.assertEqual(len(hosts.HostList), 3)
    found = 0
    for h in hosts.HostList.values():
      if h.PhysAddress == 'f8:8f:ca:00:00:01':
        self.assertEqual(h.Layer1Interface, 'Device.Foo.Interface.1')
        self.assertEqual(h.IPAddress, '192.168.1.1')
        found |= 1
      elif h.PhysAddress == 'f8:8f:ca:00:00:02':
        self.assertEqual(h.Layer1Interface, 'Device.Foo.Interface.2')
        self.assertEqual(h.IPAddress, '192.168.1.2')
        found |= 2
      elif h.PhysAddress == 'f8:8f:ca:00:00:03':
        self.assertEqual(h.Layer1Interface, 'Device.Foo.Interface.1')
        self.assertEqual(h.IPAddress, '192.168.1.3')
        found |= 4
    self.assertEqual(found, 7)

  def testDhcpFingerprint(self):
    host.PROC_NET_ARP = 'testdata/host/proc_net_arp'
    iflookup = {'foo0': 'Device.Foo.Interface.1',
                'foo1': 'Device.Foo.Interface.2'}
    hosts = host.Hosts(iflookup)
    self.assertEqual(len(hosts.HostList), 3)
    found = 0
    for h in hosts.HostList.values():
      fp = h.X_CATAWAMPUS_ORG_ClientIdentification.DhcpFingerprint
      if h.PhysAddress == 'f8:8f:ca:00:00:01':
        self.assertEqual(fp, '1,2,3')
        found |= 1
      elif h.PhysAddress == 'f8:8f:ca:00:00:02':
        self.assertEqual(fp, '4,5,6')
        found |= 2
      elif h.PhysAddress == 'f8:8f:ca:00:00:03':
        self.assertEqual(fp, '')
        found |= 4
    self.assertEqual(found, 7)

  def testNoDhcpFingerprintFile(self):
    host.PROC_NET_ARP = 'testdata/host/proc_net_arp'
    host.DHCP_FINGERPRINTS = '/nonexistent'
    hosts = host.Hosts()
    self.assertEqual(len(hosts.HostList), 3)
    for h in hosts.HostList.values():
      fp = h.X_CATAWAMPUS_ORG_ClientIdentification.DhcpFingerprint
      self.assertEqual(fp, '')

  def testCorruptDhcpFingerprintFile(self):
    host.PROC_NET_ARP = 'testdata/host/proc_net_arp'
    host.DHCP_FINGERPRINTS = 'testdata/host/fingerprints-corrupt'
    hosts = host.Hosts()
    self.assertEqual(len(hosts.HostList), 3)
    for h in hosts.HostList.values():
      fp = h.X_CATAWAMPUS_ORG_ClientIdentification.DhcpFingerprint
      self.assertEqual(fp, '')

  def testEmptyDhcpFingerprintFile(self):
    host.PROC_NET_ARP = 'testdata/host/proc_net_arp'
    host.DHCP_FINGERPRINTS = 'testdata/host/fingerprints-empty'
    hosts = host.Hosts()
    self.assertEqual(len(hosts.HostList), 3)
    for h in hosts.HostList.values():
      fp = h.X_CATAWAMPUS_ORG_ClientIdentification.DhcpFingerprint
      self.assertEqual(fp, '')

  def _GetFakeCPE(self, tr98=True, tr181=True):
    igd = device = None
    device_id = platform.fakecpe.device.DeviceIdFakeCPE()
    if tr98:
      igd = platform.fakecpe.device.InternetGatewayDeviceFakeCPE(
          device_id=device_id)
    if tr181:
      device = platform.fakecpe.device.DeviceFakeCPE(device_id=device_id)
    return TestDeviceModelRoot(tr98=igd, tr181=device)

  def testTr98(self):
    dmroot = self._GetFakeCPE(tr98=True, tr181=False)
    hosts = host.Hosts(dmroot=dmroot)
    self.assertEqual(len(hosts.HostList), 2)
    found = 0
    for h in hosts.HostList.values():
      l1interface = 'InternetGatewayDevice.LANDevice.1.WLANConfiguration.1'
      self.assertEqual(h.Layer1Interface, l1interface)
      if h.PhysAddress == '00:01:02:03:04:05':
        self.assertFalse(found & 0x1)
        found |= 0x1
        a = l1interface + '.AssociatedDevice.1'
        self.assertEqual(h.AssociatedDevice, a)
      elif h.PhysAddress == '00:01:02:03:04:06':
        self.assertFalse(found & 0x2)
        found |= 0x2
        a = l1interface + '.AssociatedDevice.2'
        self.assertEqual(h.AssociatedDevice, a)
    self.assertEqual(found, 0x3)

  def testTr181(self):
    dmroot = self._GetFakeCPE(tr98=False, tr181=True)
    hosts = host.Hosts(dmroot=dmroot)
    self.assertEqual(len(hosts.HostList), 3)
    found = 0
    for h in hosts.HostList.values():
      l1interface = 'Device.MoCA.Interface.1'
      if h.PhysAddress == '00:11:22:33:44:11':
        self.assertFalse(found & 0x1)
        found |= 0x1
        # Fields from MoCA AssocidatedDevice table
        self.assertEqual(h.Layer1Interface, l1interface)
        a = l1interface + '.AssociatedDevice.1'
        self.assertEqual(h.AssociatedDevice, a)
        # Fields from fake_dhcp_server.py
        self.assertEqual(h.IPAddress, '192.168.133.7')
        self.assertEqual(h.ClientID, 'client_id1')
        self.assertEqual(h.IPv4AddressNumberOfEntries, 2)
        self.assertEqual(h.IPv4AddressList['1'].IPAddress, '192.168.133.7')
        self.assertEqual(h.IPv4AddressList['2'].IPAddress, '192.168.1.1')
      elif h.PhysAddress == '00:11:22:33:44:22':
        self.assertFalse(found & 0x2)
        found |= 0x2
        self.assertEqual(h.Layer1Interface, l1interface)
        a = l1interface + '.AssociatedDevice.2'
        self.assertEqual(h.AssociatedDevice, a)
      elif h.PhysAddress == '00:11:22:33:44:33':
        self.assertFalse(found & 0x4)
        found |= 0x4
        # populated by fake_dhcp_server.py
        self.assertEqual(h.IPAddress, '192.168.133.8')
        self.assertEqual(h.HostName, 'hostname_2')
        self.assertEqual(h.IPv4AddressNumberOfEntries, 1)
        self.assertEqual(h.IPv4AddressList['1'].IPAddress, '192.168.133.8')
    self.assertEqual(found, 0x7)


if __name__ == '__main__':
  unittest.main()

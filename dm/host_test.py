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

"""Unit tests for host.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import datetime
import google3
from tr.wvtest import unittest
import platform.fakecpe.device
import tr.core
import tr.handle
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


def FakeWifiTaxonomy(unused_signature, mac):
  if mac in ['f8:8f:ca:00:00:04', 'f8:8f:ca:00:00:05']:
    return ('chipset', 'model', '802.11ac n:4,w:80')
  return ('', '', '')


def FakeWifiCharacterization(unused_signature):
  return ('802.11ac', 4, '80')


class HostTest(unittest.TestCase):

  def setUp(self):
    self.old_DHCP_TAXONOMY_FILE = host.DHCP_TAXONOMY_FILE
    self.old_DNSSD_HOSTNAMES = host.DNSSD_HOSTNAMES
    self.old_IP6NEIGH = host.IP6NEIGH[0]
    self.old_NETBIOS_HOSTNAMES = host.NETBIOS_HOSTNAMES
    self.old_PROC_NET_ARP = host.PROC_NET_ARP
    self.old_SYS_CLASS_NET_PATH = host.SYS_CLASS_NET_PATH
    self.old_TAXONOMIZE = host.TAXONOMIZE
    self.old_WIFICHARACTERIZE = host.WIFICHARACTERIZE
    self.old_TIMENOW = host.TIMENOW
    self.old_WIFI_TAXONOMY_DIR = host.WIFI_TAXONOMY_DIR
    self.old_WIFIBLASTER_DIR = host.WIFIBLASTER_DIR
    host.DHCP_TAXONOMY_FILE = 'testdata/host/dhcp-taxonomy'
    host.DNSSD_HOSTNAMES = 'testdata/host/dnssd_hostnames'
    host.IP6NEIGH[0] = 'testdata/host/ip6neigh_empty'
    host.NETBIOS_HOSTNAMES = 'testdata/host/netbios_hostnames'
    host.PROC_NET_ARP = '/dev/null'
    host.SYS_CLASS_NET_PATH = 'testdata/host/sys/class/net'
    host.TAXONOMIZE = FakeWifiTaxonomy
    host.WIFICHARACTERIZE = FakeWifiCharacterization
    host.TIMENOW = TimeNow
    host.WIFI_TAXONOMY_DIR = 'testdata/host/wifi-taxonomy'
    host.WIFIBLASTER_DIR = 'testdata/host/wifiblaster'

  def tearDown(self):
    host.DHCP_TAXONOMY_FILE = self.old_DHCP_TAXONOMY_FILE
    host.DNSSD_HOSTNAMES = self.old_DNSSD_HOSTNAMES
    host.IP6NEIGH[0] = self.old_IP6NEIGH
    host.NETBIOS_HOSTNAMES = self.old_NETBIOS_HOSTNAMES
    host.PROC_NET_ARP = self.old_PROC_NET_ARP
    host.SYS_CLASS_NET_PATH = self.old_SYS_CLASS_NET_PATH
    host.TAXONOMIZE = self.old_TAXONOMIZE
    host.WIFICHARACTERIZE = self.old_WIFICHARACTERIZE
    host.TIMENOW = self.old_TIMENOW
    host.WIFI_TAXONOMY_DIR = self.old_WIFI_TAXONOMY_DIR
    host.WIFIBLASTER_DIR = self.old_WIFIBLASTER_DIR

  def testValidateExports(self):
    hosts = host.Hosts()
    tr.handle.ValidateExports(hosts)
    h = host.Host()
    tr.handle.ValidateExports(h)

  def testHostFields(self):
    h = host.Host(Active=True, PhysAddress='00:00:00:00:00:00',
                  ip4=['ip4_1', 'ip4_2', 'ip4_3'],
                  ip6=['ip6_1', 'ip6_2', 'ip6_3', 'ip6_4'],
                  DHCPClient='dhcpclient',
                  AssociatedDevice='associated_device',
                  Layer1Interface='l1iface', Layer3Interface='l3iface',
                  HostName='hostname', LeaseTimeRemaining=1000,
                  VendorClassID='vendor_class_id',
                  ClientID='client_id', UserClassID='user_class_id')
    tr.handle.ValidateExports(h)
    self.assertEqual(True, h.Active)
    self.assertEqual('associated_device', h.AssociatedDevice)
    self.assertEqual('client_id', h.ClientID)
    self.assertEqual('dhcpclient', h.DHCPClient)
    self.assertEqual('hostname', h.HostName)
    self.assertEqual('ip4_1', h.IPAddress)
    self.assertEqual('ip4_1', h.IP4Address)
    self.assertEqual('ip6_1', h.IP6Address)
    self.assertEqual('l1iface', h.Layer1Interface)
    self.assertEqual('l3iface', h.Layer3Interface)
    self.assertEqual(1000, h.LeaseTimeRemaining)
    self.assertEqual('00:00:00:00:00:00', h.PhysAddress)
    self.assertEqual('user_class_id', h.UserClassID)
    self.assertEqual('vendor_class_id', h.VendorClassID)
    self.assertEqual(3, len(h.IPv4AddressList))
    self.assertEqual('ip4_1', h.IPv4AddressList['1'].IPAddress)
    self.assertEqual('ip4_2', h.IPv4AddressList['2'].IPAddress)
    self.assertEqual('ip4_3', h.IPv4AddressList['3'].IPAddress)
    tr.handle.ValidateExports(h.IPv4AddressList['1'])
    tr.handle.ValidateExports(h.IPv4AddressList['2'])
    tr.handle.ValidateExports(h.IPv4AddressList['3'])
    self.assertEqual(4, len(h.IPv6AddressList))
    self.assertEqual('ip6_1', h.IPv6AddressList['1'].IPAddress)
    self.assertEqual('ip6_2', h.IPv6AddressList['2'].IPAddress)
    self.assertEqual('ip6_3', h.IPv6AddressList['3'].IPAddress)
    self.assertEqual('ip6_4', h.IPv6AddressList['4'].IPAddress)
    tr.handle.ValidateExports(h.IPv6AddressList['1'])
    tr.handle.ValidateExports(h.IPv6AddressList['2'])
    tr.handle.ValidateExports(h.IPv6AddressList['3'])
    tr.handle.ValidateExports(h.IPv6AddressList['4'])

  def testHostsFromBridge(self):
    iflookup = {'eth0': 'Ethernet', 'eth1.0': 'MoCA'}
    h = host.Hosts(iflookup, bridgename='br0')
    self.assertEqual(10, len(h.HostList))
    tr.handle.ValidateExports(h)
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
      self.assertEqual(expected[entry.PhysAddress], entry.Layer1Interface)
      self.assertTrue(entry.Active)
      del expected[entry.PhysAddress]
      tr.handle.ValidateExports(entry)
    self.assertEqual(0, len(expected))

  def testMissingFdbFile(self):
    iflookup = {'eth0': 'Ethernet', 'eth1.0': 'MoCA'}
    h = host.Hosts(iflookup, bridgename='nonexistent0')
    self.assertEqual(0, len(h.HostList))

  def testGetHostsFromArp(self):
    host.PROC_NET_ARP = 'testdata/host/proc_net_arp'
    iflookup = {'foo0': 'Device.Foo.Interface.1',
                'foo1': 'Device.Foo.Interface.2'}
    hosts = host.Hosts(iflookup)
    self.assertEqual(3, len(hosts.HostList))
    found = 0
    for h in hosts.HostList.values():
      self.assertTrue(h.Active)
      if h.PhysAddress == 'f8:8f:ca:00:00:01':
        self.assertEqual('Device.Foo.Interface.1', h.Layer1Interface)
        self.assertEqual('192.168.1.1', h.IPAddress)
        found |= 1
      elif h.PhysAddress == 'f8:8f:ca:00:00:02':
        self.assertEqual('Device.Foo.Interface.2', h.Layer1Interface)
        self.assertEqual('192.168.1.2', h.IPAddress)
        found |= 2
      elif h.PhysAddress == 'f8:8f:ca:00:00:03':
        self.assertEqual('Device.Foo.Interface.1', h.Layer1Interface)
        self.assertEqual('192.168.1.3', h.IPAddress)
        found |= 4
    self.assertEqual(7, found)

  def testGetHostsFromIp6Neigh(self):
    host.IP6NEIGH[0] = 'testdata/host/ip6neigh'
    iflookup = {'foo0': 'Device.Foo.Interface.1',
                'foo1': 'Device.Foo.Interface.2'}
    hosts = host.Hosts(iflookup)
    self.assertEqual(3, len(hosts.HostList))
    found = 0
    for h in hosts.HostList.values():
      if h.PhysAddress == 'f8:8f:ca:00:00:01':
        self.assertEqual('Device.Foo.Interface.1', h.Layer1Interface)
        self.assertEqual('fe80::fa8f:caff:fe00:1', h.IPAddress)
        self.assertTrue(h.Active)
        found |= 1
      elif h.PhysAddress == 'f8:8f:ca:00:00:02':
        self.assertEqual('Device.Foo.Interface.1', h.Layer1Interface)
        self.assertEqual('fe80::fa8f:caff:fe00:2', h.IPAddress)
        self.assertFalse(h.Active)
        found |= 2
      elif h.PhysAddress == 'f8:8f:ca:00:00:03':
        self.assertEqual('Device.Foo.Interface.2', h.Layer1Interface)
        self.assertEqual('fe80::fa8f:caff:fe00:3', h.IPAddress)
        self.assertTrue(h.Active)
        found |= 4
    self.assertEqual(7, found)

  def testDhcpTaxonomy(self):
    host.PROC_NET_ARP = 'testdata/host/proc_net_arp'
    iflookup = {'foo0': 'Device.Foo.Interface.1',
                'foo1': 'Device.Foo.Interface.2'}
    hosts = host.Hosts(iflookup)
    self.assertEqual(3, len(hosts.HostList))
    found = 0
    for h in hosts.HostList.values():
      fp = h.X_CATAWAMPUS_ORG_ClientIdentification.DhcpTaxonomy
      if h.PhysAddress == 'f8:8f:ca:00:00:01':
        self.assertEqual('1,2,3', fp)
        found |= 1
      elif h.PhysAddress == 'f8:8f:ca:00:00:02':
        self.assertEqual('4,5,6', fp)
        found |= 2
      elif h.PhysAddress == 'f8:8f:ca:00:00:03':
        self.assertEqual('', fp)
        found |= 4
    self.assertEqual(7, found)

  def testNoDhcpTaxonomyFile(self):
    host.PROC_NET_ARP = 'testdata/host/proc_net_arp'
    host.DHCP_TAXONOMY_FILE = '/nonexistent'
    hosts = host.Hosts()
    self.assertEqual(3, len(hosts.HostList))
    for h in hosts.HostList.values():
      fp = h.X_CATAWAMPUS_ORG_ClientIdentification.DhcpTaxonomy
      self.assertEqual('', fp)

  def testCorruptDhcpTaxonomyFile(self):
    host.PROC_NET_ARP = 'testdata/host/proc_net_arp'
    host.DHCP_TAXONOMY_FILE = 'testdata/host/dhcp-taxonomy-corrupt'
    hosts = host.Hosts()
    self.assertEqual(3, len(hosts.HostList))
    for h in hosts.HostList.values():
      fp = h.X_CATAWAMPUS_ORG_ClientIdentification.DhcpTaxonomy
      self.assertEqual('', fp)

  def testEmptyDhcpTaxonomyFile(self):
    host.PROC_NET_ARP = 'testdata/host/proc_net_arp'
    host.DHCP_TAXONOMY_FILE = 'testdata/host/dhcp-taxonomy-empty'
    hosts = host.Hosts()
    self.assertEqual(3, len(hosts.HostList))
    for h in hosts.HostList.values():
      fp = h.X_CATAWAMPUS_ORG_ClientIdentification.DhcpTaxonomy
      self.assertEqual('', fp)

  def testWifiTaxonomyAndBlaster(self):
    host.PROC_NET_ARP = 'testdata/host/proc_net_arp2'
    dmroot = self._GetFakeCPE(tr98=False, tr181=True)
    hosts = host.Hosts(dmroot=dmroot)
    found = 0
    for h in hosts.HostList.values():
      # Note that there are several more hosts in the list, supplied
      # by the fake_dhcp_server.py, but not relevant to this test case.
      ci = h.X_CATAWAMPUS_ORG_ClientIdentification
      if h.PhysAddress == 'f8:8f:ca:00:00:04':
        expected = 'wifi|probe:1,2,3,4|assoc:5,6,7,8'
        self.assertEqual(ci.WifiTaxonomy.strip(), expected)
        self.assertEqual(ci.WifiChipset.strip(), 'chipset')
        self.assertEqual(ci.WifiDeviceModel.strip(), 'model')
        self.assertEqual(ci.WifiPerformance.strip(), '802.11ac n:4,w:80')
        self.assertEqual(ci.WifiStandard.strip(), '802.11ac')
        self.assertEqual(ci.WifiNumberOfStreams, 4)
        self.assertEqual(ci.WifiChannelWidth.strip(), '80')
        self.assertEqual(ci.WifiblasterLatestResult,
                         '1440647444 version=2 mac=f8:8f:ca:00:00:04 '
                         'throughput=587176800 rssi=-39 frequency=5745 '
                         'samples=664440000,602112000,705600000,573888000,'
                         '682080000,602112000,686784000,301056000,499800000,'
                         '553896000')
        self.assertEqual(ci.WifiblasterLatestTime,
                         datetime.datetime(2015, 8, 27, 3, 50, 44))
        self.assertEqual(ci.WifiblasterLatestFrequency, 5745)
        self.assertEqual(ci.WifiblasterLatestRSSI, -39)
        self.assertEqual(ci.WifiblasterLatestThroughput, 587176800)
        found |= 1
      elif h.PhysAddress == 'f8:8f:ca:00:00:05':
        expected = 'wifi|probe:1,2,3,4|assoc:5,6,7,8'
        self.assertEqual(ci.WifiTaxonomy.strip(), expected)
        self.assertEqual(ci.WifiChipset.strip(), 'chipset')
        self.assertEqual(ci.WifiDeviceModel.strip(), 'model')
        self.assertEqual(ci.WifiPerformance.strip(), '802.11ac n:4,w:80')
        self.assertEqual(ci.WifiStandard.strip(), '802.11ac')
        self.assertEqual(ci.WifiNumberOfStreams, 4)
        self.assertEqual(ci.WifiChannelWidth.strip(), '80')
        # fake_dhcp_server.py says this is MyPhone, which is fine.
        self.assertEqual(h.HostName, 'MyPhone')
        found |= 2
      elif h.PhysAddress == 'f8:8f:ca:00:00:06':
        found |= 4
    self.assertEqual(7, found)

  def testHostnames4(self):
    host.PROC_NET_ARP = 'testdata/host/proc_net_arp'
    hosts = host.Hosts()
    self.assertEqual(3, len(hosts.HostList))
    found = 0
    for h in hosts.HostList.values():
      cid = h.X_CATAWAMPUS_ORG_ClientIdentification
      if h.PhysAddress == 'f8:8f:ca:00:00:01':
        self.assertEqual('192.168.1.1', h.IPAddress)
        self.assertEqual('dnssd_hostname4_1.local', cid.DnsSdName)
        self.assertEqual('NETBIOS_HOSTNAME4_1', cid.NetbiosName)
        cid = h.X_CATAWAMPUS_ORG_ClientIdentification
        found |= 1
      elif h.PhysAddress == 'f8:8f:ca:00:00:02':
        self.assertEqual('192.168.1.2', h.IPAddress)
        self.assertEqual('dnssd_hostname4_2.local', cid.DnsSdName)
        self.assertEqual('NETBIOS_HOSTNAME4_2', cid.NetbiosName)
        self.assertEqual('dnssd_hostname4_2', h.HostName)
        found |= 2
      elif h.PhysAddress == 'f8:8f:ca:00:00:03':
        self.assertEqual('192.168.1.3', h.IPAddress)
        self.assertEqual('', cid.DnsSdName)
        self.assertEqual('NETBIOS_HOSTNAME4_3', cid.NetbiosName)
        self.assertEqual('NETBIOS_HOSTNAME4_3', h.HostName)
        found |= 4
    self.assertEqual(7, found)

  def testHostnames6(self):
    host.IP6NEIGH[0] = 'testdata/host/ip6neigh'
    hosts = host.Hosts()
    self.assertEqual(3, len(hosts.HostList))
    found = 0
    for h in hosts.HostList.values():
      cid = h.X_CATAWAMPUS_ORG_ClientIdentification
      if h.PhysAddress == 'f8:8f:ca:00:00:01':
        self.assertEqual('fe80::fa8f:caff:fe00:1', h.IPAddress)
        self.assertEqual('dnssd_hostname6_1.local', cid.DnsSdName)
        self.assertEqual('NETBIOS_HOSTNAME6_1', cid.NetbiosName)
        found |= 1
      elif h.PhysAddress == 'f8:8f:ca:00:00:02':
        self.assertEqual('fe80::fa8f:caff:fe00:2', h.IPAddress)
        self.assertEqual('dnssd_hostname6_2.local', cid.DnsSdName)
        self.assertEqual('NETBIOS_HOSTNAME6_2', cid.NetbiosName)
        self.assertEqual('dnssd_hostname6_2', h.HostName)
        found |= 2
      elif h.PhysAddress == 'f8:8f:ca:00:00:03':
        self.assertEqual('fe80::fa8f:caff:fe00:3', h.IPAddress)
        self.assertEqual('', cid.DnsSdName)
        self.assertEqual('NETBIOS_HOSTNAME6_3', cid.NetbiosName)
        self.assertEqual('NETBIOS_HOSTNAME6_3', h.HostName)
        found |= 4
    self.assertEqual(7, found)

  def testHostnameCorruptedFile(self):
    host.PROC_NET_ARP = 'testdata/host/proc_net_arp'
    host.NETBIOS_HOSTNAMES = 'testdata/host/netbios_hostnames_corrupt'
    hosts = host.Hosts()
    self.assertEqual(3, len(hosts.HostList))
    found = False
    for h in hosts.HostList.values():
      if h.PhysAddress == 'f8:8f:ca:00:00:03':
        self.assertEqual('NETBIOS_HOSTNAME4_3', h.HostName)
        found = True
    self.assertTrue(found)

  def testHostnameInvalidUnicode(self):
    host.PROC_NET_ARP = 'testdata/host/proc_net_arp'
    host.DNSSD_HOSTNAMES = 'testdata/host/dnssd_hostnames_invalid_unicode'
    hosts = host.Hosts()
    self.assertEqual(3, len(hosts.HostList))
    found = False
    for h in hosts.HostList.values():
      cid = h.X_CATAWAMPUS_ORG_ClientIdentification
      if h.PhysAddress == 'f8:8f:ca:00:00:01':
        self.assertEqual(
            u'dnssd_hostname_invalidUTF8_\ufffd.local', cid.DnsSdName)
        found = True
    self.assertTrue(found)

  def _GetFakeCPE(self, tr98=True, tr181=True):
    igd = device = None
    device_id = platform.fakecpe.device.DeviceId()
    if tr98:
      igd = platform.fakecpe.device.InternetGatewayDeviceFakeCPE(
          device_id=device_id)
    if tr181:
      device = platform.fakecpe.device.DeviceFakeCPE(device_id=device_id)
    return tr.handle.Handle(TestDeviceModelRoot(tr98=igd, tr181=device))

  def testTr98(self):
    dmroot = self._GetFakeCPE(tr98=True, tr181=False)
    hosts = host.Hosts(dmroot=dmroot)
    self.assertEqual(2, len(hosts.HostList))
    found = 0
    for h in hosts.HostList.values():
      self.assertTrue(h.Active)
      l1interface = 'InternetGatewayDevice.LANDevice.1.WLANConfiguration.1'
      self.assertEqual(l1interface, h.Layer1Interface)
      if h.PhysAddress == '00:01:02:03:04:05':
        self.assertFalse(found & 0x1)
        found |= 0x1
        a = l1interface + '.AssociatedDevice.1'
        self.assertEqual(a, h.AssociatedDevice)
      elif h.PhysAddress == '00:01:02:03:04:06':
        self.assertFalse(found & 0x2)
        found |= 0x2
        a = l1interface + '.AssociatedDevice.2'
        self.assertEqual(a, h.AssociatedDevice)
    self.assertEqual(0x3, found)

  def testTr181(self):
    dmroot = self._GetFakeCPE(tr98=False, tr181=True)
    hosts = host.Hosts(dmroot=dmroot)
    self.assertEqual(6, len(hosts.HostList))
    found = 0
    for h in hosts.HostList.values():
      l1interface = 'Device.MoCA.Interface.1'
      if h.PhysAddress == '00:11:22:33:44:11':
        self.assertTrue(h.Active)
        self.assertFalse(found & 0x1)
        found |= 0x1
        # Fields from MoCA AssocidatedDevice table
        self.assertEqual(l1interface, h.Layer1Interface)
        a = l1interface + '.AssociatedDevice.1'
        self.assertEqual(a, h.AssociatedDevice)
        # Fields from fake_dhcp_server.py
        self.assertEqual('192.168.133.7', h.IPAddress)
        self.assertEqual('client_id1', h.ClientID)
        self.assertEqual(2, h.IPv4AddressNumberOfEntries)
        self.assertEqual('192.168.133.7', h.IPv4AddressList['1'].IPAddress)
        self.assertEqual('192.168.1.1', h.IPv4AddressList['2'].IPAddress)
      elif h.PhysAddress == '00:11:22:33:44:22':
        self.assertTrue(h.Active)
        self.assertFalse(found & 0x2)
        found |= 0x2
        self.assertEqual(l1interface, h.Layer1Interface)
        a = l1interface + '.AssociatedDevice.2'
        self.assertEqual(a, h.AssociatedDevice)
      elif h.PhysAddress == '00:11:22:33:44:33':
        self.assertFalse(h.Active)
        self.assertFalse(found & 0x4)
        found |= 0x4
        # populated by fake_dhcp_server.py
        self.assertEqual('192.168.133.8', h.IPAddress)
        self.assertEqual('hostname_2', h.HostName)
        self.assertEqual(1, h.IPv4AddressNumberOfEntries)
        self.assertEqual('192.168.133.8', h.IPv4AddressList['1'].IPAddress)
      elif h.PhysAddress == 'f8:8f:ca:00:00:04':
        found |= 0x8
      elif h.PhysAddress == 'f8:8f:ca:00:00:05':
        found |= 0x10
      elif h.PhysAddress == 'f8:8f:ca:00:00:06':
        found |= 0x20
    self.assertEqual(0x3f, found)


if __name__ == '__main__':
  unittest.main()

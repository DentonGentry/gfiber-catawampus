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
#pylint: disable-msg=C6409

"""Unit tests for host.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import unittest

import google3
import host


def TimeNow():
  return 1384057000.0


class HostTest(unittest.TestCase):
  def setUp(self):
    self.old_SYS_CLASS_NET_PATH = host.SYS_CLASS_NET_PATH
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
    iflookup = { 'eth0': 'Ethernet', 'eth1.0': 'MoCA', }
    h = host.Hosts(iflookup, bridgename='br0')
    self.assertEqual(len(h.HostList), 10)
    # brforward file taken from a real system in the lab
    self.assertEqual(h.HostList['1'].PhysAddress, 'e8:39:35:b8:66:c8')
    self.assertEqual(h.HostList['1'].Layer1Interface, 'Ethernet')
    self.assertEqual(h.HostList['2'].PhysAddress, '68:05:ca:16:2a:90')
    self.assertEqual(h.HostList['2'].Layer1Interface, 'Ethernet')
    self.assertEqual(h.HostList['3'].PhysAddress, '28:c0:da:3a:b4:15')
    self.assertEqual(h.HostList['3'].Layer1Interface, 'Ethernet')
    self.assertEqual(h.HostList['4'].PhysAddress, 'f8:8f:ca:00:c4:47')
    self.assertEqual(h.HostList['4'].Layer1Interface, 'MoCA')
    self.assertEqual(h.HostList['5'].PhysAddress, 'f8:8f:ca:00:da:6c')
    self.assertEqual(h.HostList['5'].Layer1Interface, 'Ethernet')
    self.assertEqual(h.HostList['6'].PhysAddress, 'f8:8f:ca:09:4e:25')
    self.assertEqual(h.HostList['6'].Layer1Interface, 'MoCA')
    self.assertEqual(h.HostList['7'].PhysAddress, 'f8:8f:ca:00:c2:df')
    self.assertEqual(h.HostList['7'].Layer1Interface, 'Ethernet')
    self.assertEqual(h.HostList['8'].PhysAddress, 'f8:8f:ca:00:c2:47')
    self.assertEqual(h.HostList['8'].Layer1Interface, 'Ethernet')
    self.assertEqual(h.HostList['9'].PhysAddress, '00:00:de:ad:be:ef')
    self.assertEqual(h.HostList['9'].Layer1Interface, 'Ethernet')
    self.assertEqual(h.HostList['10'].PhysAddress, 'ac:4b:c8:7e:32:04')
    self.assertEqual(h.HostList['10'].Layer1Interface, 'Ethernet')
    h.ValidateExports()
    h.HostList['1'].ValidateExports()
    h.HostList['2'].ValidateExports()
    h.HostList['3'].ValidateExports()
    h.HostList['4'].ValidateExports()
    h.HostList['5'].ValidateExports()
    h.HostList['6'].ValidateExports()
    h.HostList['7'].ValidateExports()
    h.HostList['8'].ValidateExports()
    h.HostList['9'].ValidateExports()
    h.HostList['10'].ValidateExports()

  def testMissingFdbFile(self):
    iflookup = { 'eth0': 'Ethernet', 'eth1.0': 'MoCA', }
    h = host.Hosts(iflookup, bridgename='nonexistent0')
    self.assertEqual(len(h.HostList), 0)

  def testDnsmasqLeases(self):
    h = host.Hosts(iflookup={}, dnsmasqfile='testdata/host/dnsmasq.leases')
    self.assertEqual(len(h.HostList), 3)
    found = 0
    for hostentry in h.HostList.values():
      self.assertEqual(hostentry.AddressSource, 'DHCP')
      mac = hostentry.PhysAddress
      if mac == '00:01:02:03:04:01':
        found |= 1
        self.assertEqual(hostentry.LeaseTimeRemaining, 0)
        self.assertEqual(hostentry.ClientID, '')
        self.assertEqual(hostentry.HostName, 'host-1')
        ipl = hostentry.IPv4AddressList
        self.assertEqual(len(ipl), 1)
        self.assertEqual(ipl['1'].IPAddress, '192.168.1.1')
      if mac == '00:01:02:03:04:02':
        found |= 2
        self.assertEqual(hostentry.LeaseTimeRemaining, 1000)
        # 'client-id-2' == 636c69656e742d69642d32
        self.assertEqual(hostentry.ClientID, '636c69656e742d69642d32')
        self.assertEqual(hostentry.HostName, 'host-2')
        self.assertEqual(len(hostentry.IPv4AddressList), 1)
        ipl = hostentry.IPv4AddressList
        self.assertEqual(len(ipl), 1)
        self.assertEqual(ipl['1'].IPAddress, '192.168.1.2')
      if mac == '00:01:02:03:04:03':
        found |= 4
        self.assertEqual(hostentry.LeaseTimeRemaining, 2000)
        # 'client-id-3' == 636c69656e742d69642d33
        self.assertEqual(hostentry.ClientID, '636c69656e742d69642d33')
        self.assertEqual(hostentry.HostName, '')
        self.assertEqual(len(hostentry.IPv4AddressList), 1)
        ipl = hostentry.IPv4AddressList
        self.assertEqual(len(ipl), 1)
        self.assertEqual(ipl['1'].IPAddress, '192.168.1.3')
    self.assertEqual(found, 7)

  def testDnsmasqCorrupt(self):
    h = host.Hosts(iflookup={}, dnsmasqfile='testdata/host/dnsmasq.corrupt')
    self.assertEqual(len(h.HostList), 0)

  def testMissingDnsmasqFile(self):
    h = host.Hosts(iflookup={}, dnsmasqfile='/nonexistent')
    self.assertEqual(len(h.HostList), 0)


if __name__ == '__main__':
  unittest.main()

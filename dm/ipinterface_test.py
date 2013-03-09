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

"""Unit tests for tr-181 Device.IP.Interface implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import socket
import unittest
import google3
import ipinterface
import netdev


class IpInterfaceTest(unittest.TestCase):
  """Tests for ipinterface.py."""

  def setUp(self):
    self.old_IFADDRESSES = ipinterface.IFADDRESSES
    self.old_PROC_NET_DEV = netdev.PROC_NET_DEV
    self.old_PYNETIFCONF = ipinterface.PYNETIFCONF
    ipinterface.IFADDRESSES = MockIfaddresses
    ipinterface.PYNETIFCONF = MockPynet
    netdev.PROC_NET_DEV = 'testdata/ethernet/net_dev'

  def tearDown(self):
    ipinterface.PYNETIFCONF = self.old_PYNETIFCONF
    netdev.PROC_NET_DEV = self.old_PROC_NET_DEV

  def testValidateExports(self):
    ip = ipinterface.IPInterfaceLinux26('foo0')
    ip.ValidateExports()

  def testInterfaceStatsGood(self):
    ip = ipinterface.IPInterfaceStatsLinux26('foo0')
    ip.ValidateExports()
    # only a sanity check. Extensive tests in netdev_test.py
    self.assertEqual(ip.PacketsSent, 10)

  def testInterfaceParams(self):
    ip = ipinterface.IPInterfaceLinux26('foo0')
    self.assertEqual(ip.MaxMTUSize, 1499)

  def testInterfaceIPLists(self):
    ip = ipinterface.IPInterfaceLinux26('foo0')
    self.assertEqual(ip.IPv4AddressNumberOfEntries, 2)
    self.assertEqual(ip.IPv4AddressList[0].IPAddress, '1.1.1.3')
    self.assertEqual(ip.IPv4AddressList[0].SubnetMask, '255.255.255.0')
    self.assertTrue(ip.IPv4AddressList[0].Enable)
    self.assertEqual(ip.IPv4AddressList[0].Status, 'Enabled')
    self.assertEqual(ip.IPv4AddressList[1].IPAddress, '2.2.2.3')
    self.assertEqual(ip.IPv4AddressList[1].SubnetMask, '255.255.254.0')
    self.assertTrue(ip.IPv4AddressList[1].Enable)
    self.assertEqual(ip.IPv4AddressList[1].Status, 'Enabled')
    self.assertEqual(ip.IPv6AddressNumberOfEntries, 2)
    self.assertEqual(ip.IPv6AddressList[0].IPAddress,
                     '1000:1000:1000:1000:0011:22ff:fe33:4455')
    self.assertTrue(ip.IPv6AddressList[0].Enable)
    self.assertEqual(ip.IPv6AddressList[0].IPAddressStatus,
                     'Preferred')
    self.assertEqual(ip.IPv6AddressList[1].IPAddress,
                     'fe80::0011:22ff:fe33:4455')
    self.assertTrue(ip.IPv6AddressList[1].Enable)
    self.assertEqual(ip.IPv6AddressList[1].IPAddressStatus,
                     'Preferred')

  def testInterfaceIPListsEmpty(self):
    ip = ipinterface.IPInterfaceLinux26('foo1')
    self.assertEqual(ip.IPv4AddressNumberOfEntries, 0)
    self.assertEqual(ip.IPv6AddressNumberOfEntries, 0)


class MockPynet(object):
  v_is_up = True
  v_mtu = 1499

  def __init__(self, ifname):
    self.ifname = ifname

  def is_up(self):
    return self.v_is_up

  def get_mtu(self):
    return self.v_mtu


def MockIfaddresses(iface):
  if iface == 'foo0':
    return {
        socket.AF_PACKET: [{'broadcast': 'ff:ff:ff:ff:ff:ff',
                            'addr': '00:11:22:33:44:55'}],
        socket.AF_INET: [{'broadcast': '1.1.1.255',
                          'netmask': '255.255.255.0',
                          'addr': '1.1.1.3'},
                         {'broadcast': '2.2.2.255',
                          'netmask': '255.255.254.0',
                          'addr': '2.2.2.3'}
                         ],
        socket.AF_INET6: [{'netmask': 'ffff:ffff:ffff:ffff::',
                           'addr': '1000:1000:1000:1000:0011:22ff:fe33:4455'},
                          {'netmask': 'ffff:ffff:ffff:ffff::',
                           'addr': 'fe80::0011:22ff:fe33:4455'}]
    }
  if iface == 'foo1':
    return {
        socket.AF_PACKET: [{'broadcast': 'ff:ff:ff:ff:ff:ff',
                            'addr': '00:11:22:33:44:66'}]
    }



if __name__ == '__main__':
  unittest.main()

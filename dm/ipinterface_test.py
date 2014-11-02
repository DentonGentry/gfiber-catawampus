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

import os
import shutil
import socket
import tempfile
import google3
from tr.wvtest import unittest
import ipinterface
import netdev
import tr.mainloop
import tr.session


class IpInterfaceTest(unittest.TestCase):
  """Tests for ipinterface.py."""

  def setUp(self):
    self.loop = tr.mainloop.MainLoop()
    self.old_PROC_NET_DEV = netdev.PROC_NET_DEV
    self.old_PYNETIFCONF = ipinterface.PYNETIFCONF
    ipinterface.IFADDRESSES = MockIfaddresses
    ipinterface.PYNETIFCONF = MockPynet
    netdev.PROC_NET_DEV = 'testdata/ipinterface/net_dev'
    tr.session.cache.flush()
    self.test_dir = tempfile.mkdtemp()
    ipinterface.IPCONFIG = ['testdata/ipinterface/ip-config', self.test_dir]

  def tearDown(self):
    ipinterface.PYNETIFCONF = self.old_PYNETIFCONF
    netdev.PROC_NET_DEV = self.old_PROC_NET_DEV
    shutil.rmtree(self.test_dir)

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
    self.assertEqual(ip.IPv4AddressList['1'].IPAddress, '1.1.1.3')
    self.assertEqual(ip.IPv4AddressList['1'].SubnetMask, '255.255.255.0')
    self.assertTrue(ip.IPv4AddressList['1'].Enable)
    self.assertEqual(ip.IPv4AddressList['1'].Status, 'Enabled')
    self.assertEqual(ip.IPv4AddressList['2'].IPAddress, '2.2.2.3')
    self.assertEqual(ip.IPv4AddressList['2'].SubnetMask, '255.255.254.0')
    self.assertTrue(ip.IPv4AddressList['2'].Enable)
    self.assertEqual(ip.IPv4AddressList['2'].Status, 'Enabled')
    self.assertEqual(ip.IPv6AddressNumberOfEntries, 2)
    ip6a = ip.IPv6AddressList['1']
    self.assertEqual(ip6a.IPAddress, '1000:1000:1000:1000:0011:22ff:fe33:4455')
    self.assertTrue(ip6a.Enable)
    self.assertEqual(ip6a.IPAddressStatus, 'Preferred')
    ip6a = ip.IPv6AddressList['2']
    self.assertEqual(ip6a.IPAddress, 'fe80::0011:22ff:fe33:4455')
    self.assertTrue(ip6a.Enable)
    self.assertEqual(ip6a.IPAddressStatus, 'Preferred')

  def testInterfaceIPparams(self):
    ip = ipinterface.IPInterfaceLinux26('foo0')
    self.assertEqual(ip.X_CATAWAMPUS_ORG_IP4Address, '1.1.1.3')
    self.assertEqual(ip.X_CATAWAMPUS_ORG_IP6Address,
                     '1000:1000:1000:1000:0011:22ff:fe33:4455')

  def testInterfaceIPListsEmpty(self):
    ip = ipinterface.IPInterfaceLinux26('foo1')
    self.assertEqual(ip.IPv4AddressNumberOfEntries, 0)
    self.assertEqual(ip.IPv6AddressNumberOfEntries, 0)

  def testInterfaceIP4Write(self):
    out = os.path.join(self.test_dir, 'ip-add')
    ip = ipinterface.IPInterfaceLinux26('foo0')
    ip.IPv4AddressList['1'].IPAddress = '1.1.1.4'
    self.loop.RunOnce(timeout=1)
    buf = open(out).read()
    expected = 'foo0 1.1.1.4/24 2.2.2.3/23'
    self.assertEqual(buf, expected)
    ip.IPv4AddressList['1'].SubnetMask = '255.0.0.0'
    self.loop.RunOnce(timeout=1)
    buf = open(out).read()
    expected = 'foo0 1.1.1.4/8 2.2.2.3/23'
    self.assertEqual(buf, expected)
    ip.IPv4AddressList['1'].IPAddress = ''
    ip.IPv4AddressList['1'].SubnetMask = ''
    del ip.IPv4AddressList['2']
    self.loop.RunOnce(timeout=1)
    buf = open(out).read()
    self.assertEqual(buf, 'foo0')

  def testConvertMaskToCIDR(self):
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.255.255'), 32)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.255.254'), 31)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.255.252'), 30)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.255.248'), 29)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.255.240'), 28)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.255.224'), 27)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.255.192'), 26)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.255.128'), 25)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.255.0'), 24)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.254.0'), 23)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.252.0'), 22)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.248.0'), 21)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.240.0'), 20)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.224.0'), 19)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.192.0'), 18)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.128.0'), 17)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.255.0.0'), 16)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.254.0.0'), 15)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.252.0.0'), 14)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.248.0.0'), 13)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.240.0.0'), 12)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.224.0.0'), 11)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.192.0.0'), 10)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.128.0.0'), 9)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('255.0.0.0'), 8)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('254.0.0.0'), 7)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('252.0.0.0'), 6)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('248.0.0.0'), 5)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('240.0.0.0'), 4)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('224.0.0.0'), 3)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('192.0.0.0'), 2)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('128.0.0.0'), 1)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('0.0.0.0'), 0)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('0.1.0.0'), -1)
    self.assertEqual(ipinterface._ConvertMaskToCIDR('0.0.0.255'), -1)


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
                           'addr': 'fe80::0011:22ff:fe33:4455%foo0'}]
    }
  if iface == 'foo1':
    return {
        socket.AF_PACKET: [{'broadcast': 'ff:ff:ff:ff:ff:ff',
                            'addr': '00:11:22:33:44:66'}]
    }



if __name__ == '__main__':
  unittest.main()

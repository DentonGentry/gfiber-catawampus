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
# pylint: disable-msg=C6409

"""Unit tests for netdev.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
from tr.wvtest import unittest
import netdev


class NetdevTest(unittest.TestCase):
  """Tests for netdev.py."""

  def setUp(self):
    self._old_PROC_NET_DEV = netdev.PROC_NET_DEV

  def tearDown(self):
    netdev.PROC_NET_DEV = self._old_PROC_NET_DEV

  def testInterfaceStatsGood(self):
    netdev.PROC_NET_DEV = 'testdata/ethernet/net_dev'
    eth = netdev.NetdevStatsLinux26(ifname='foo0')
    self.assertEqual(eth.BroadcastPacketsReceived, 0)
    self.assertEqual(eth.BroadcastPacketsSent, 0)
    self.assertEqual(eth.BytesReceived, 1)
    self.assertEqual(eth.BytesSent, 9)
    self.assertEqual(eth.DiscardPacketsReceived, 9)
    self.assertEqual(eth.DiscardPacketsSent, 11)
    self.assertEqual(eth.ErrorsReceived, 9)
    self.assertEqual(eth.ErrorsSent, 12)
    self.assertEqual(eth.MulticastPacketsReceived, 8)
    self.assertEqual(eth.MulticastPacketsSent, 0)
    self.assertEqual(eth.PacketsReceived, 100)
    self.assertEqual(eth.PacketsSent, 10)
    self.assertEqual(eth.UnicastPacketsReceived, 92)
    self.assertEqual(eth.UnicastPacketsSent, 10)
    self.assertEqual(eth.UnknownProtoPacketsReceived, 0)

  def testInterfaceStatsReal(self):
    # A test using a /proc/net/dev line taken from a running Linux 2.6.32
    # system. Most of the fields are zero, so we exercise the other handling
    # using the foo0 fake data instead.
    netdev.PROC_NET_DEV = 'testdata/ethernet/net_dev'
    eth = netdev.NetdevStatsLinux26('eth0')
    self.assertEqual(eth.BroadcastPacketsReceived, 0)
    self.assertEqual(eth.BroadcastPacketsSent, 0)
    self.assertEqual(eth.BytesReceived, 21052761139)
    self.assertEqual(eth.BytesSent, 10372833035)
    self.assertEqual(eth.DiscardPacketsReceived, 0)
    self.assertEqual(eth.DiscardPacketsSent, 0)
    self.assertEqual(eth.ErrorsReceived, 0)
    self.assertEqual(eth.ErrorsSent, 0)
    self.assertEqual(eth.MulticastPacketsReceived, 0)
    self.assertEqual(eth.MulticastPacketsSent, 0)
    self.assertEqual(eth.PacketsReceived, 91456760)
    self.assertEqual(eth.PacketsSent, 80960002)
    self.assertEqual(eth.UnicastPacketsReceived, 91456760)
    self.assertEqual(eth.UnicastPacketsSent, 80960002)
    self.assertEqual(eth.UnknownProtoPacketsReceived, 0)

  def testSysfsStats(self):
    qfiles = 'testdata/sysfs/eth0/bcmgenet_discard_cnt_q%d'
    numq = 17
    eth = netdev.NetdevStatsLinux26('eth0', qfiles=qfiles,
                                    numq=numq, hipriq=numq)
    self.assertEqual(len(eth.X_CATAWAMPUS_ORG_DiscardFrameCnts), numq)
    total = 0
    for i in range(numq):
      self.assertEqual(int(eth.X_CATAWAMPUS_ORG_DiscardFrameCnts[i]), i)
      total += i
    self.assertEqual(eth.X_CATAWAMPUS_ORG_DiscardPacketsReceivedHipri, total)

    numq = 5
    eth = netdev.NetdevStatsLinux26('eth0', qfiles=qfiles, numq=numq, hipriq=2)
    self.assertEqual(len(eth.X_CATAWAMPUS_ORG_DiscardFrameCnts), numq)
    for i in range(numq):
      self.assertEqual(int(eth.X_CATAWAMPUS_ORG_DiscardFrameCnts[i]), i)
    self.assertEqual(eth.X_CATAWAMPUS_ORG_DiscardPacketsReceivedHipri, 1)

    eth = netdev.NetdevStatsLinux26('foo0', qfiles=qfiles, numq=0)
    self.assertEqual(len(eth.X_CATAWAMPUS_ORG_DiscardFrameCnts), 0)
    self.assertEqual(eth.X_CATAWAMPUS_ORG_DiscardPacketsReceivedHipri, 0)

  def testRxPacketsWrap(self):
    """Rx Packets has wrapped back to zero, but Rx Multicast has not."""
    netdev.PROC_NET_DEV = 'testdata/netdev/wrapped_net_dev'
    eth = netdev.NetdevStatsLinux26('eth0')
    self.assertEqual(eth.MulticastPacketsReceived, 10)
    self.assertEqual(eth.PacketsReceived, 1)
    # b/12022359 would try to set UnicastPacketsReceived negative, and result
    # in a ValueError. We want to check that no exception is raised.
    self.assertGreater(eth.UnicastPacketsReceived, 0)


if __name__ == '__main__':
  unittest.main()

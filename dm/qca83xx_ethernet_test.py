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

"""Unit tests for QCA83xx Ethernet.* implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
from tr.wvtest import unittest
import tr.handle
import qca83xx_ethernet


MOCKPORTSETFIELDS = {}


class QcaEthernetTest(unittest.TestCase):
  """Tests for qca83xx_ethernet.py."""

  def setUp(self):
    self.old_QCAPORT = qca83xx_ethernet.QCAPORT
    self.mac = 'f8:8f:ca:ff:ff:02'
    MOCKPORTSETFIELDS.clear()

  def tearDown(self):
    qca83xx_ethernet.QCAPORT = self.old_QCAPORT
    self.eth = None

  def testValidateExports(self):
    qca83xx_ethernet.QCAPORT = MockPortStats
    eth = qca83xx_ethernet.EthernetInterfaceQca83xx(portnum=1, mac=self.mac,
                                                    ifname='foo0')
    tr.handle.ValidateExports(eth)

  def testStats(self):
    qca83xx_ethernet.QCAPORT = MockPortStats
    eth = qca83xx_ethernet.EthernetInterfaceQca83xx(portnum=1, mac=self.mac,
                                                    ifname='foo0')
    self.assertEqual(eth.Stats.BytesSent, 17000000000000000L)
    self.assertEqual(eth.Stats.BytesReceived, 36000000000000000L)
    self.assertEqual(eth.Stats.PacketsSent, 15 + 19 + 25)
    self.assertEqual(eth.Stats.PacketsReceived, 31 + 34 + 39)
    self.assertEqual(eth.Stats.ErrorsSent, 24 + 14 + 13 + 23)
    self.assertEqual(eth.Stats.ErrorsReceived, 37 + 41 + 30 + 40 + 29 + 35)
    self.assertEqual(eth.Stats.UnicastPacketsSent, 25)
    self.assertEqual(eth.Stats.UnicastPacketsReceived, 31)
    self.assertEqual(eth.Stats.MulticastPacketsSent, 15)
    self.assertEqual(eth.Stats.MulticastPacketsReceived, 39)
    self.assertEqual(eth.Stats.BroadcastPacketsSent, 19)
    self.assertEqual(eth.Stats.BroadcastPacketsReceived, 34)
    self.assertEqual(eth.Stats.DiscardPacketsSent, 0)
    self.assertEqual(eth.Stats.DiscardPacketsReceived, 0)
    self.assertEqual(eth.Stats.UnknownProtoPacketsReceived, 0)

  def testFields(self):
    qca83xx_ethernet.QCAPORT = MockPortStats
    eth = qca83xx_ethernet.EthernetInterfaceQca83xx(portnum=1, mac=self.mac,
                                                    ifname='foo0')
    self.assertEqual(eth.MaxBitRate, 100)
    self.assertEqual(eth.DuplexMode, 'full')
    self.assertEqual(eth.Status, 'Up')
    self.assertEqual(eth.MACAddress, self.mac)
    self.assertFalse(eth.Upstream)

  def testStatus(self):
    qca83xx_ethernet.QCAPORT = MockPortLinkFault
    eth = qca83xx_ethernet.EthernetInterfaceQca83xx(portnum=1, mac=self.mac,
                                                    ifname='foo0')
    self.assertEqual(eth.Status, 'Error')
    qca83xx_ethernet.QCAPORT = MockPortLinkDown
    eth = qca83xx_ethernet.EthernetInterfaceQca83xx(portnum=1, mac=self.mac,
                                                    ifname='foo0')
    self.assertEqual(eth.Status, 'Down')

  def testWrite(self):
    qca83xx_ethernet.QCAPORT = MockPortLinkDown
    eth = qca83xx_ethernet.EthernetInterfaceQca83xx(portnum=1, mac=self.mac,
                                                    ifname='foo0')
    eth.DuplexMode = 'full'
    self.assertTrue('duplex' in MOCKPORTSETFIELDS)
    self.assertEqual(MOCKPORTSETFIELDS['duplex'], 'full')
    eth.MaxBitRate = 1000
    self.assertTrue('speed' in MOCKPORTSETFIELDS)
    self.assertEqual(MOCKPORTSETFIELDS['speed'], 1000)

  def testGetAssociatedDevices(self):
    qca83xx_ethernet.QCAPORT = MockPortLinkDown
    eth = qca83xx_ethernet.EthernetInterfaceQca83xx(portnum=1, mac=self.mac,
                                                    ifname='foo0')
    ac = eth.GetAssociatedDevices()
    self.assertEqual(len(ac), 3)
    self.assertEqual(ac[0]['PhysAddress'], 'f8:8f:ca:00:00:01')
    self.assertEqual(ac[1]['PhysAddress'], 'f8:8f:ca:00:00:02')
    self.assertEqual(ac[2]['PhysAddress'], 'f8:8f:ca:00:00:03')


class MockPortLinkDown(object):

  def __init__(self, port):
    self.port = port

  def CableDiag(self):
    return [('normal', 1), ('normal', 1), ('normal', 1), ('normal', 1)]

  def Duplex(self, duplex=None):
    if duplex:
      MOCKPORTSETFIELDS['duplex'] = duplex
    return 'half'

  def Fdb(self):
    return [{'PhysAddress': 'f8:8f:ca:00:00:01', 'Ports': ['qca83xx_1']},
            {'PhysAddress': 'f8:8f:ca:00:00:02', 'Ports': ['qca83xx_1']},
            {'PhysAddress': 'f8:8f:ca:00:00:03', 'Ports': ['qca83xx_1']},
            {'PhysAddress': '01:00:5e:00:00:fb', 'Ports': ['qca83xx_1']}]

  def IsLinkUp(self):
    return False

  def Speed(self, speed=None):
    if speed:
      MOCKPORTSETFIELDS['speed'] = speed
    return 10

  def Stats(self):
    return {}


class MockPortLinkFault(object):

  def __init__(self, port):
    self.port = port

  def CableDiag(self):
    return [('normal', 1), ('shorted', 1000), ('normal', 1), ('normal', 1)]

  def Duplex(self, duplex=None):
    if duplex:
      MOCKPORTSETFIELDS['duplex'] = duplex
    return 'half'

  def Fdb(self):
    return [{'PhysAddress': 'f8:8f:ca:00:00:01', 'Ports': ['qca83xx_1']},
            {'PhysAddress': 'f8:8f:ca:00:00:02', 'Ports': ['qca83xx_1']},
            {'PhysAddress': 'f8:8f:ca:00:00:03', 'Ports': ['qca83xx_1']}]

  def IsLinkUp(self):
    return False

  def Speed(self, speed=None):
    if speed:
      MOCKPORTSETFIELDS['speed'] = speed
    return 10

  def Stats(self):
    return {}


class MockPortStats(object):

  def __init__(self, port):
    self.port = port
    self.stats_read = 0

  def CableDiag(self):
    return [('normal', 1), ('normal', 1), ('normal', 1), ('normal', 1)]

  def Duplex(self, duplex=None):
    if duplex:
      MOCKPORTSETFIELDS['duplex'] = duplex
    return 'full'

  def Fdb(self):
    return [{'PhysAddress': 'f8:8f:ca:00:00:01', 'Ports': ['qca83xx_1']},
            {'PhysAddress': 'f8:8f:ca:00:00:02', 'Ports': ['qca83xx_1']},
            {'PhysAddress': 'f8:8f:ca:00:00:03', 'Ports': ['qca83xx_1']}]

  def IsLinkUp(self):
    return True

  def Speed(self, speed=None):
    if speed:
      MOCKPORTSETFIELDS['speed'] = speed
    return 100

  def Stats(self):
    self.stats_read += 1
    if self.stats_read > 1:
      return {}
    else:
      return {'Tx64BytePackets': 1,
              'Tx65_128BytePackets': 2,
              'Tx129_256BytePackets': 3,
              'Tx257_512BytePackets': 4,
              'Tx513_1024BytePackets': 5,
              'Tx1025_1518BytePackets': 6,

              'Rx64BytePackets': 7,
              'Rx65_128BytePackets': 8,
              'Rx129_256BytePackets': 9,
              'Rx257_512BytePackets': 10,
              'Rx513_1024BytePackets': 11,
              'Rx1025_1518BytePackets': 12,

              'TxLateCollisions': 13,
              'TxOverSizePackets': 14,
              'TxMulticastPackets': 15,
              'TxSingleCollisions': 16,
              'TxBytes': 17000000000000000L,
              'TxMultipleCollisions': 18,
              'TxBroadcastPackets': 19,
              'TxCollisions': 20,
              'TxPauseFrames': 21,
              'TxMaxBytePackets': 22,
              'TxExcessiveDeferrals': 23,
              'TxUnderRuns': 24,
              'TxUnicastPackets': 25,
              'TxDeferrals': 26,
              'TxAbortedCollisions': 27,

              'FilteredPackets': 28,

              'RxTooLongPackets': 29,
              'RxRuntPackets': 30,
              'RxUnicastPackets': 31,
              'RxBadBytes': 32000000000000000L,
              'RxMaxBytePackets': 33,
              'RxBroadcastPackets': 34,
              'RxOverFlows': 35,
              'RxGoodBytes': 36000000000000000L,
              'RxFcsErrors': 37,
              'RxPauseFrames': 38,
              'RxMulticastPackets': 39,
              'RxFragments': 40,
              'RxAlignmentErrors': 41}


if __name__ == '__main__':
  unittest.main()

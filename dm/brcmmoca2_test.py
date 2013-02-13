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
# pylint: disable-msg=C6409

"""Unit tests for tr-181 Device.MoCA.* implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import unittest
import google3
import tr.session
import brcmmoca2
import netdev


class MocaTest(unittest.TestCase):
  """Tests for brcmmoca2.py."""

  def setUp(self):
    self.old_MOCAP = brcmmoca2.MOCAP
    self.old_PYNETIFCONF = brcmmoca2.PYNETIFCONF
    self.old_PROC_NET_DEV = netdev.PROC_NET_DEV
    brcmmoca2.MOCAP = 'testdata/brcmmoca2/mocap'
    brcmmoca2.PYNETIFCONF = MockPynet
    netdev.PROC_NET_DEV = 'testdata/brcmmoca2/proc/net/dev'
    tr.session.cache.flush()

  def tearDown(self):
    brcmmoca2.MOCAP = self.old_MOCAP
    brcmmoca2.PYNETIFCONF = self.old_PYNETIFCONF
    netdev.PROC_NET_DEV = self.old_PROC_NET_DEV

  def testMocaInterfaceStatsGood(self):
    moca = brcmmoca2.BrcmMocaInterfaceStatsLinux26('foo0')
    moca.ValidateExports()

    self.assertEqual(moca.BroadcastPacketsReceived, 0)
    self.assertEqual(moca.BroadcastPacketsSent, 0)
    self.assertEqual(moca.BytesReceived, 1)
    self.assertEqual(moca.BytesSent, 9)
    self.assertEqual(moca.DiscardPacketsReceived, 4)
    self.assertEqual(moca.DiscardPacketsSent, 11)
    self.assertEqual(moca.ErrorsReceived, 9)
    self.assertEqual(moca.ErrorsSent, 12)
    self.assertEqual(moca.MulticastPacketsReceived, 8)
    self.assertEqual(moca.MulticastPacketsSent, 0)
    self.assertEqual(moca.PacketsReceived, 100)
    self.assertEqual(moca.PacketsSent, 10)
    self.assertEqual(moca.UnicastPacketsReceived, 92)
    self.assertEqual(moca.UnicastPacketsSent, 10)
    self.assertEqual(moca.UnknownProtoPacketsReceived, 0)

  def testMocaInterfaceStatsNonexistent(self):
    moca = brcmmoca2.BrcmMocaInterfaceStatsLinux26('doesnotexist0')
    exception_raised = False
    try:
      moca.ErrorsReceived
    except AttributeError:
      exception_raised = True
    self.assertTrue(exception_raised)

  def testMocaInterface(self):
    moca = brcmmoca2.BrcmMocaInterface(ifname='foo0', upstream=False)
    moca.ValidateExports()
    self.assertEqual(moca.Name, 'foo0')
    self.assertEqual(moca.LowerLayers, '')
    self.assertFalse(moca.Upstream)
    self.assertEqual(moca.MACAddress, MockPynet.v_mac)
    self.assertEqual(moca.MaxNodes, 16)
    moca = brcmmoca2.BrcmMocaInterface(ifname='foo0', upstream=True)
    self.assertTrue(moca.Upstream)
    MockPynet.v_is_up = True
    MockPynet.v_link_up = True
    self.assertEqual(moca.Status, 'Up')
    MockPynet.v_link_up = False
    self.assertEqual(moca.Status, 'Dormant')
    MockPynet.v_is_up = False
    self.assertEqual(moca.Status, 'Down')
    self.assertEqual(moca.FirmwareVersion, '5.6.789')
    self.assertEqual(moca.HighestVersion, '2.0')
    self.assertEqual(moca.CurrentVersion, '2.0')
    self.assertEqual(moca.BackupNC, 5)
    self.assertEqual(moca.LastChange, 6090)
    self.assertEqual(moca.PreferredNC, False)
    self.assertFalse(moca.PrivacyEnabled)
    self.assertEqual(moca.CurrentOperFreq, 575000000)
    self.assertEqual(moca.LastOperFreq, 575000000)
    self.assertEqual(moca.NetworkCoordinator, 1)
    self.assertEqual(moca.NodeID, 2)
    self.assertTrue(moca.QAM256Capable)
    self.assertEqual(moca.PacketAggregationCapability, 20)
    # Read-only parameter
    self.assertRaises(AttributeError, setattr, moca, 'QAM256Capable', True)

  def testMocaInterfaceAlt(self):
    brcmmoca2.MOCAP = 'testdata/brcmmoca2/mocap_alt'
    moca = brcmmoca2.BrcmMocaInterface(ifname='foo0', upstream=False)
    self.assertEqual(moca.HighestVersion, '1.0')
    self.assertEqual(moca.CurrentVersion, '1.0')
    self.assertEqual(moca.BackupNC, 2)
    self.assertEqual(moca.PreferredNC, True)
    self.assertTrue(moca.PrivacyEnabled)
    self.assertFalse(moca.QAM256Capable)
    self.assertEqual(moca.PacketAggregationCapability, 7)

  def testMocaInterfaceMocaCtlFails(self):
    brcmmoca2.MOCAP = 'testdata/brcmmoca2/mocap_fail'
    moca = brcmmoca2.BrcmMocaInterface(ifname='foo0', upstream=False)
    self.assertEqual(moca.FirmwareVersion, '0')
    self.assertEqual(moca.HighestVersion, '0.0')
    self.assertEqual(moca.CurrentVersion, '0.0')
    self.assertEqual(moca.BackupNC, 0)
    self.assertFalse(moca.PrivacyEnabled)
    self.assertFalse(moca.QAM256Capable)
    self.assertEqual(moca.PacketAggregationCapability, 0)

  def testLastChange(self):
    moca = brcmmoca2.BrcmMocaInterface(ifname='foo0', upstream=False)
    brcmmoca2.MOCAP = 'testdata/brcmmoca2/mocap_uptime'
    self.assertEqual(moca.LastChange, 119728800)

  def testAssociatedDevice(self):
    moca = brcmmoca2.BrcmMocaInterface(ifname='foo0', upstream=False)
    self.assertEqual(2, moca.AssociatedDeviceNumberOfEntries)

    ad = moca.GetAssociatedDevice(1)
    ad.ValidateExports()
    self.assertTrue(ad.Active)
    self.assertEqual(ad.MACAddress, '00:01:00:11:23:33')
    self.assertEqual(ad.NodeID, 1)
    self.assertEqual(ad.PHYTxRate, 690)
    self.assertEqual(ad.PHYRxRate, 680)
    self.assertEqual(ad.RxPowerLevel, 25)
    self.assertEqual(ad.X_CATAWAMPUS_ORG_RxPowerLevel_dBm, -25.250)
    self.assertEqual(ad.TxBcastRate, 670)
    self.assertEqual(ad.RxBcastPowerLevel, 25)
    self.assertEqual(ad.X_CATAWAMPUS_ORG_RxBcastPowerLevel_dBm, -25.100)
    self.assertEqual(ad.TxPackets, 1)
    self.assertEqual(ad.RxPackets, 2)
    self.assertEqual(ad.RxErroredAndMissedPackets, 11)
    self.assertEqual(ad.RxSNR, 38)
    self.assertEqual(ad.X_CATAWAMPUS_ORG_RxSNR_dB, 38.063)
    self.assertEqual(
        ad.X_CATAWAMPUS_ORG_TxBitloading,
        '$BRCM2$'
        '00001111111111111111111111111111'
        '22222222222222222222222222222222'
        '33333333333333333333333333333333'
        '44444444444444444444444444444444'
        '55555555555555555555555555555555'
        '66666666666666666666666666666666'
        '77777777777777777777777777777777'
        '88888888888888888888888888888888'
        '99999999999999999999999999999999'
        'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
        'cccccccccccccccccccccccccccccccc'
        'dddddddddddddddddddddddddddddddd'
        'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
        'ffffffffffffffffffffffffffffffff'
        '00002222222222222222222222222222')
    self.assertEqual(
        ad.X_CATAWAMPUS_ORG_RxBitloading,
        '$BRCM2$'
        '11111111111111111111111111110000'
        '22222222222222222222222222220000'
        '33333333333333333333333333330000'
        '44444444444444444444444444440000'
        '55555555555555555555555555550000'
        '66666666666666666666666666660000'
        '77777777777777777777777777770000'
        '88888888888888888888888888880000'
        '99999999999999999999999999990000'
        'aaaaaaaaaaaaaaaaaaaaaaaaaaaa0000'
        'bbbbbbbbbbbbbbbbbbbbbbbbbbbb0000'
        'cccccccccccccccccccccccccccc0000'
        'dddddddddddddddddddddddddddd0000'
        'eeeeeeeeeeeeeeeeeeeeeeeeeeee0000'
        'ffffffffffffffffffffffffffff0000'
        '00000000000000000000000000001111')

    ad = moca.GetAssociatedDevice(4)
    ad.ValidateExports()
    self.assertTrue(ad.Active)
    self.assertEqual(ad.MACAddress, '00:01:00:11:23:44')
    self.assertEqual(ad.NodeID, 4)
    # read-only parameters
    self.assertRaises(AttributeError, setattr, ad, 'MACAddress', 'foo')
    self.assertRaises(AttributeError, setattr, ad, 'NodeID', 2)
    self.assertRaises(AttributeError, setattr, ad, 'PHYTxRate', 1)
    self.assertRaises(AttributeError, setattr, ad, 'PHYRxRate', 1)
    self.assertRaises(AttributeError, setattr, ad, 'RxPowerLevel', 1)
    self.assertRaises(AttributeError, setattr, ad, 'TxBcastRate', 1)
    self.assertRaises(AttributeError, setattr, ad, 'RxBcastPowerLevel', 1)
    self.assertRaises(AttributeError, setattr, ad, 'TxPackets', 1)
    self.assertRaises(AttributeError, setattr, ad, 'RxPackets', 1)
    self.assertRaises(AttributeError, setattr, ad,
                      'RxErroredAndMissedPackets', 1)
    self.assertRaises(AttributeError, setattr, ad, 'RxSNR', 39)

  def testCombineBitloading(self):
    bitlines = ['008 - 015:  22222222', '000 - 007:  11111111',
                '024 - 031:  44444444', '016 - 023:  33333333']
    self.assertEqual(brcmmoca2._CombineBitloading(bitlines),
                     '11111111222222223333333344444444')


class MockPynet(object):
  v_is_up = True
  v_mac = '00:11:22:33:44:55'
  v_speed = 1000
  v_duplex = True
  v_auto = True
  v_link_up = True

  def __init__(self, ifname):
    self.ifname = ifname

  def is_up(self):
    return self.v_is_up

  def get_mac(self):
    return self.v_mac

  def get_link_info(self):
    return (self.v_speed, self.v_duplex, self.v_auto, self.v_link_up)


if __name__ == '__main__':
  unittest.main()

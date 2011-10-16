#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for tr-181 Ethernet.* implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import unittest
import ethernet
import tr.core
import tr.tr181_v2_2 as tr181

BASEETHERNET = tr181.Device_v2_2.Device.Ethernet


class EthernetTest(unittest.TestCase):
  """Tests for ethernet.py."""
  def testInterfaceStatsGood(self):
    devstat = ethernet.NetdevStatsLinux26("testdata/ethernet/net_dev")
    eth = ethernet.EthernetInterfaceStatsLinux26("foo0", devstat)
    try:
      eth.ValidateExports()
    except SchemaError:
      self.AssertTrue(False)

    self.assertEqual(eth.BroadcastPacketsReceived, None)
    self.assertEqual(eth.BroadcastPacketsSent, None)
    self.assertEqual(eth.BytesReceived, '1')
    self.assertEqual(eth.BytesSent, '9')
    self.assertEqual(eth.DiscardPacketsReceived, '4')
    self.assertEqual(eth.DiscardPacketsSent, '11')
    self.assertEqual(eth.ErrorsReceived, '9')
    self.assertEqual(eth.ErrorsSent, '12')
    self.assertEqual(eth.MulticastPacketsReceived, '8')
    self.assertEqual(eth.MulticastPacketsSent, None)
    self.assertEqual(eth.PacketsReceived, '100')
    self.assertEqual(eth.PacketsSent, '10')
    self.assertEqual(eth.UnicastPacketsReceived, '92')
    self.assertEqual(eth.UnicastPacketsSent, '10')
    self.assertEqual(eth.UnknownProtoPacketsReceived, None)

  def testInterfaceStatsReal(self):
    # A test using a /proc/net/dev line taken from a running Linux 2.6.32
    # system. Most of the fields are zero, so we exercise the other handling
    # using the foo0 fake data instead.
    devstat = ethernet.NetdevStatsLinux26("testdata/ethernet/net_dev")
    eth = ethernet.EthernetInterfaceStatsLinux26("eth0", devstat)
    try:
      eth.ValidateExports()
    except SchemaError:
      self.AssertTrue(False)

    self.assertEqual(eth.BroadcastPacketsReceived, None)
    self.assertEqual(eth.BroadcastPacketsSent, None)
    self.assertEqual(eth.BytesReceived, '21052761139')
    self.assertEqual(eth.BytesSent, '10372833035')
    self.assertEqual(eth.DiscardPacketsReceived, '0')
    self.assertEqual(eth.DiscardPacketsSent, '0')
    self.assertEqual(eth.ErrorsReceived, '0')
    self.assertEqual(eth.ErrorsSent, '0')
    self.assertEqual(eth.MulticastPacketsReceived, '0')
    self.assertEqual(eth.MulticastPacketsSent, None)
    self.assertEqual(eth.PacketsReceived, '91456760')
    self.assertEqual(eth.PacketsSent, '80960002')
    self.assertEqual(eth.UnicastPacketsReceived, '91456760')
    self.assertEqual(eth.UnicastPacketsSent, '80960002')
    self.assertEqual(eth.UnknownProtoPacketsReceived, None)

  def testInterfaceStatsNonexistent(self):
    devstat = ethernet.NetdevStatsLinux26("testdata/ethernet/net_dev")
    self.assertRaises(TypeError, ethernet.EthernetInterfaceStatsLinux26,
                      "doesnotexist0", devstat)

  def _CheckEthernetInterfaceParameters(self, ifname, eth, pynet):
    self.assertEqual(eth.Alias, ifname)
    self.assertEqual(eth.DuplexMode, 'Auto')
    self.assertEqual(eth.Enable, True)
    self.assertEqual(eth.LastChange, 0)
    self.assertEqual(eth.LowerLayers, None)
    self.assertEqual(eth.MACAddress, pynet.v_mac)
    self.assertEqual(eth.MaxBitRate, -1)
    self.assertEqual(eth.Name, ifname)

  def testInterfaceGood(self):
    ifstats = MockIfStats()
    pynet = MockPynet()
    ifname = "foo0"

    ethroot = ethernet.Ethernet()
    ethroot.add_interface(ifname, False, ethernet.EthernetInterfaceLinux26)
    eth = ethernet.EthernetInterfaceLinux26(ifname, ifstats, pynet)
    self._CheckEthernetInterfaceParameters(ifname, eth, pynet)

    eth = ethernet.EthernetInterfaceLinux26(ifname, ifstats, pynet)
    self._CheckEthernetInterfaceParameters(ifname, eth, pynet)

    pynet.v_is_up = False
    eth = ethernet.EthernetInterfaceLinux26(ifname, ifstats, pynet)
    self._CheckEthernetInterfaceParameters(ifname, eth, pynet)

    pynet.v_duplex = False
    eth = ethernet.EthernetInterfaceLinux26(ifname, ifstats, pynet)
    self._CheckEthernetInterfaceParameters(ifname, eth, pynet)

    pynet.v_auto = False
    eth = ethernet.EthernetInterfaceLinux26(ifname, ifstats, pynet)
    self._CheckEthernetInterfaceParameters(ifname, eth, pynet)

    pynet.v_link_up = False
    eth = ethernet.EthernetInterfaceLinux26(ifname, ifstats, pynet)
    self._CheckEthernetInterfaceParameters(ifname, eth, pynet)

    eth.ValidateExports()


class MockPynet(object):
  v_is_up = True
  v_mac = "00:11:22:33:44:55"
  v_speed = 1000
  v_duplex = True
  v_auto = True
  v_link_up = True

  def is_up(self):
    return self.v_is_up

  def get_mac(self):
    return self.v_mac

  def get_link_info(self):
    return (self.v_speed, self.v_duplex, self.v_auto, self.v_link_up)


class MockIfStats(BASEETHERNET.Interface.Stats):
  BroadcastPacketsReceived = None
  BroadcastPacketsSent = None
  BytesReceived = None
  BytesSent = None
  DiscardPacketsReceived = None
  DiscardPacketsSent = None
  ErrorsReceived = None
  ErrorsSent = None
  MulticastPacketsReceived = None
  MulticastPacketsSent = None
  PacketsReceived = None
  PacketsSent = None
  UnicastPacketsReceived = None
  UnicastPacketsSent = None
  UnknownProtoPacketsReceived = None


if __name__ == '__main__':
  unittest.main()

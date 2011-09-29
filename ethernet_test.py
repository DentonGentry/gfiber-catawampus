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


class EthernetTest(unittest.TestCase):
  """Tests for ethernet.py."""
  def testGoodIfName(self):
    eth = ethernet.EthernetInterfaceStatsLinux26("foo0",
                                                 "testdata/ethernet/net_dev")
    self.assertEqual(eth.BroadcastPacketsReceived(), None)
    self.assertEqual(eth.BroadcastPacketsSent(), None)
    self.assertEqual(eth.BytesReceived(), '1')
    self.assertEqual(eth.BytesSent(), '9')
    self.assertEqual(eth.DiscardPacketsReceived(), '4')
    self.assertEqual(eth.DiscardPacketsSent(), '11')
    self.assertEqual(eth.ErrorsReceived(), '9')
    self.assertEqual(eth.ErrorsSent(), '12')
    self.assertEqual(eth.MulticastPacketsReceived(), '8')
    self.assertEqual(eth.MulticastPacketsSent(), None)
    self.assertEqual(eth.PacketsReceived(), '100')
    self.assertEqual(eth.PacketsSent(), '10')
    self.assertEqual(eth.UnicastPacketsReceived(), '92')
    self.assertEqual(eth.UnicastPacketsSent(), '10')
    self.assertEqual(eth.UnknownProtoPacketsReceived(), None)

  def testRealLinuxCorpus(self):
    # A test using a /proc/net/dev line taken from a running Linux 2.6.32
    # system. Most of the fields are zero, so we exercise the other handling
    # using the foo0 fake data instead.
    eth = ethernet.EthernetInterfaceStatsLinux26("eth0",
                                                 "testdata/ethernet/net_dev")
    self.assertEqual(eth.BroadcastPacketsReceived(), None)
    self.assertEqual(eth.BroadcastPacketsSent(), None)
    self.assertEqual(eth.BytesReceived(), '21052761139')
    self.assertEqual(eth.BytesSent(), '10372833035')
    self.assertEqual(eth.DiscardPacketsReceived(), '0')
    self.assertEqual(eth.DiscardPacketsSent(), '0')
    self.assertEqual(eth.ErrorsReceived(), '0')
    self.assertEqual(eth.ErrorsSent(), '0')
    self.assertEqual(eth.MulticastPacketsReceived(), '0')
    self.assertEqual(eth.MulticastPacketsSent(), None)
    self.assertEqual(eth.PacketsReceived(), '91456760')
    self.assertEqual(eth.PacketsSent(), '80960002')
    self.assertEqual(eth.UnicastPacketsReceived(), '91456760')
    self.assertEqual(eth.UnicastPacketsSent(), '80960002')
    self.assertEqual(eth.UnknownProtoPacketsReceived(), None)


if __name__ == '__main__':
  unittest.main()

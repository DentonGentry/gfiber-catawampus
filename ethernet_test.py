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
    eth = ethernet.EthernetStatsLinux26("testdata/ethernet/net_dev")
    self.assertEqual(eth.BroadcastPacketsReceived("foo0"), None)
    self.assertEqual(eth.BroadcastPacketsSent("foo0"), None)
    self.assertEqual(eth.BytesReceived("foo0"), '1')
    self.assertEqual(eth.BytesSent("foo0"), '9')
    self.assertEqual(eth.DiscardPacketsReceived("foo0"), '4')
    self.assertEqual(eth.DiscardPacketsSent("foo0"), '11')
    self.assertEqual(eth.ErrorsReceived("foo0"), '9')
    self.assertEqual(eth.ErrorsSent("foo0"), '12')
    self.assertEqual(eth.MulticastPacketsReceived("foo0"), '8')
    self.assertEqual(eth.MulticastPacketsSent("foo0"), None)
    self.assertEqual(eth.PacketsReceived("foo0"), '100')
    self.assertEqual(eth.PacketsSent("foo0"), '10')
    self.assertEqual(eth.UnicastPacketsReceived("foo0"), '92')
    self.assertEqual(eth.UnicastPacketsSent("foo0"), '10')
    self.assertEqual(eth.UnknownProtoPacketsReceived("foo0"), None)

  def testRealLinuxCorpus(self):
    # A test using a /proc/net/dev line taken from a running Linux 2.6.32
    # system. Most of the fields are zero, so we exercise the other handling
    # using the foo0 fake data instead.
    eth = ethernet.EthernetStatsLinux26("testdata/ethernet/net_dev")
    self.assertEqual(eth.BroadcastPacketsReceived("eth0"), None)
    self.assertEqual(eth.BroadcastPacketsSent("eth0"), None)
    self.assertEqual(eth.BytesReceived("eth0"), '21052761139')
    self.assertEqual(eth.BytesSent("eth0"), '10372833035')
    self.assertEqual(eth.DiscardPacketsReceived("eth0"), '0')
    self.assertEqual(eth.DiscardPacketsSent("eth0"), '0')
    self.assertEqual(eth.ErrorsReceived("eth0"), '0')
    self.assertEqual(eth.ErrorsSent("eth0"), '0')
    self.assertEqual(eth.MulticastPacketsReceived("eth0"), '0')
    self.assertEqual(eth.MulticastPacketsSent("eth0"), None)
    self.assertEqual(eth.PacketsReceived("eth0"), '91456760')
    self.assertEqual(eth.PacketsSent("eth0"), '80960002')
    self.assertEqual(eth.UnicastPacketsReceived("eth0"), '91456760')
    self.assertEqual(eth.UnicastPacketsSent("eth0"), '80960002')
    self.assertEqual(eth.UnknownProtoPacketsReceived("eth0"), None)


if __name__ == '__main__':
  unittest.main()

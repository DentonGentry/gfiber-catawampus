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
# pylint:disable=invalid-name

"""Unit tests for mrvl88610_netstats.py implementation."""

__author__ = 'jnewlin@google.com (John Newlin)'

import google3
from tr.wvtest import unittest
import dm.mrvl88601_netstats


class NetStatsTest(unittest.TestCase):
  """Tests for mrvl88610_netstats.py."""

  def testInterfaceStatsGood(self):
    dm.mrvl88601_netstats.PON_STATS_DIR = 'testdata/mrvl88601_netstats/ani'
    dm.mrvl88601_netstats.ETH_STATS_DIR = 'testdata/mrvl88601_netstats/uni'
    eth = dm.mrvl88601_netstats.NetdevStatsMrvl88601(
        'testdata/mrvl88601_netstats/uni')
    self.assertEqual(eth.BroadcastPacketsReceived, 100)
    self.assertEqual(eth.BroadcastPacketsSent, 101)
    self.assertEqual(eth.BytesReceived, 1001)
    self.assertEqual(eth.BytesSent, 1002)
    self.assertEqual(eth.DiscardPacketsReceived, 0)
    self.assertEqual(eth.DiscardPacketsSent, 0)
    self.assertEqual(eth.ErrorsReceived, 11)
    self.assertEqual(eth.ErrorsSent, 0)
    self.assertEqual(eth.MulticastPacketsReceived, 103)
    self.assertEqual(eth.MulticastPacketsSent, 104)
    self.assertEqual(eth.PacketsReceived, 500)
    self.assertEqual(eth.PacketsSent, 501)
    self.assertEqual(eth.UnicastPacketsReceived, 500-100-103)
    self.assertEqual(eth.UnicastPacketsSent, 501-101-104)
    self.assertEqual(eth.UnknownProtoPacketsReceived, 0)

    # pon stats.
    pon = dm.mrvl88601_netstats.NetdevStatsMrvl88601(
        'testdata/mrvl88601_netstats/ani')
    self.assertEqual(pon.BroadcastPacketsReceived, 200)
    self.assertEqual(pon.BroadcastPacketsSent, 201)
    self.assertEqual(pon.BytesReceived, 2001)
    self.assertEqual(pon.BytesSent, 2002)
    self.assertEqual(pon.DiscardPacketsReceived, 0)
    self.assertEqual(pon.DiscardPacketsSent, 0)
    self.assertEqual(pon.ErrorsReceived, 21)
    self.assertEqual(pon.ErrorsSent, 0)
    self.assertEqual(pon.MulticastPacketsReceived, 203)
    self.assertEqual(pon.MulticastPacketsSent, 204)
    self.assertEqual(pon.PacketsReceived, 500)
    self.assertEqual(pon.PacketsSent, 500)
    self.assertEqual(pon.UnicastPacketsReceived, 500-200-203)
    self.assertEqual(pon.UnicastPacketsSent, 500-201-204)
    self.assertEqual(eth.UnknownProtoPacketsReceived, 0)

if __name__ == '__main__':
  unittest.main()

#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for brcmwifi.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import sys
sys.path.append("../")
sys.path.append("../tr/vendor/")

import brcmwifi
import os
import unittest


class BrcmWifiTest(unittest.TestCase):
  def setUp(self):
    self.old_WL_EXE = brcmwifi.WL_EXE
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlcounters"

  def tearDown(self):
    brcmwifi.WL_EXE = self.old_WL_EXE

  def testCounters(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlcounters"
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    counters = bw._GetWlCounters()
    self.assertEqual(counters['rxrtsocast'], '93')
    self.assertEqual(counters['d11_txfrmsnt'], '0')
    self.assertEqual(counters['txfunfl'], ['59', '60', '61', '62', '63', '64'])

  def testChannel(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlchannel"
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    self.assertEqual(bw.Channel, 1)

  def testOutputContiguousRanges(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    self.assertEqual(bw._OutputContiguousRanges([1,2,3,4,5]), "1-5")
    self.assertEqual(bw._OutputContiguousRanges([1,2,3,5]), "1-3,5")
    self.assertEqual(bw._OutputContiguousRanges([1,2,3,5,6,7]), "1-3,5-7")
    self.assertEqual(bw._OutputContiguousRanges([1,2,3,5,7,8,9]), "1-3,5,7-9")
    self.assertEqual(bw._OutputContiguousRanges([1,3,5,7,9]), "1,3,5,7,9")

  def testChannels(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlchannels"
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    self.assertEqual(bw.Channels, "1-11,36,40,44,48,52,56,60,64,100,104,108,112,116,120,124,128,132,136,140,149,153,157,161,165")

  def testSSID(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlssid"
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    self.assertEqual(bw.SSID, 'MySSID')
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlssidempty"
    self.assertEqual(bw.SSID, '')


if __name__ == '__main__':
  unittest.main()

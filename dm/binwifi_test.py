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
# pylint: disable-msg=C6409

"""Unit tests for binwifi.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import stat
import tempfile
import unittest

import google3
import tr.session
import binwifi
import netdev


class BinWifiTest(unittest.TestCase):
  def setUp(self):
    self.old_BINWIFI = binwifi.BINWIFI
    self.tmpdir = tempfile.mkdtemp()
    self.wifioutfile = os.path.join(self.tmpdir, 'wifi.out')
    binwifi.BINWIFI = ['testdata/binwifi/binwifi', self.wifioutfile]
    self.old_PROC_NET_DEV = netdev.PROC_NET_DEV
    netdev.PROC_NET_DEV = 'testdata/binwifi/proc_net_dev'
    self.loop = tr.mainloop.MainLoop()
    tr.session.cache.flush()

  def tearDown(self):
    binwifi.BINWIFI = self.old_BINWIFI
    netdev.PROC_NET_DEV = self.old_PROC_NET_DEV
    shutil.rmtree(self.tmpdir)

  def testValidateExports(self):
    bw = binwifi.WlanConfiguration('wifi0')
    bw.ValidateExports()

  def testWEPKeyIndex(self):
    bw = binwifi.WlanConfiguration('wifi0')
    bw.WEPKeyIndex = 1  # should succeed
    bw.WEPKeyIndex = 2
    bw.WEPKeyIndex = 3
    bw.WEPKeyIndex = 4
    self.assertRaises(ValueError, setattr, bw, 'WEPKeyIndex', 0)
    self.assertRaises(ValueError, setattr, bw, 'WEPKeyIndex', 5)

  def testWifiStats(self):
    bw = binwifi.WlanConfiguration('wifi0')
    self.assertEqual(bw.TotalBytesReceived, 1)
    self.assertEqual(bw.TotalBytesSent, 9)
    self.assertEqual(bw.TotalPacketsReceived, 100)
    self.assertEqual(bw.TotalPacketsSent, 10)
    self.assertEqual(bw.Stats.UnicastPacketsSent, 10)

  def testConfigCommit(self):
    bw = binwifi.WlanConfiguration('wifi0')
    bw.RadioEnabled = True
    bw.AutoChannelEnable = True
    bw.SSID = 'testSSID'
    bw.BeaconType = 'WPAand11i'
    bw.IEEE11iEncryptionModes = 'AESEncryption'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    self.assertEqual(buf, 'set -b 2.4 -c auto -s testSSID -e WPA2_PSK_AES\n')

  def testSSID(self):
    bw = binwifi.WlanConfiguration('wifi0')
    bw.SSID = 'this is ok'
    bw.SSID = '0123456789abcdef0123456789abcdef'  # should still be ok
    self.assertRaises(ValueError, setattr, bw, 'SSID',
                      '0123456789abcdef0123456789abcdef0')


if __name__ == '__main__':
  unittest.main()

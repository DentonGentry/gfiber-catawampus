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

"""Unit tests for binwifi.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import stat
import tempfile

import google3
from tr.wvtest import unittest
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
    # Let any pending callbacks expire
    self.loop.RunOnce(timeout=1)

  def testValidateExports(self):
    bw = binwifi.WlanConfiguration('wifi0')
    bw.ValidateExports()

  def testWEPKeyIndex(self):
    bw = binwifi.WlanConfiguration('wifi0')
    bw.StartTransaction()
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
    bw = binwifi.WlanConfiguration('wifi0', band='2.4')
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.X_CATAWAMPUS_ORG_AutoChanType = 'HIGH'
    bw.SSID = 'Test SSID 1'
    bw.BeaconType = 'WPA'
    bw.IEEE11iEncryptionModes = 'AESEncryption'
    bw.KeyPassphrase = 'testpassword'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    # testdata/binwifi/binwifi quotes every argument
    exp = [
        '"set" "-P" "-b" "2.4" "-e" "WPA_PSK_AES" "-c" "auto" "-s" '
        '"Test SSID 1" "-a" "HIGH" "-p" "a/b/g/n"',
        'PSK=testpassword'
    ]
    self.assertEqual(buf.strip().splitlines(), exp)

  def testAnotherConfigCommit(self):
    bw = binwifi.WlanConfiguration('wifi0', band='2.4')
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = False
    bw.Channel = 10
    bw.X_CATAWAMPUS_ORG_AutoChanType = 'HIGH'
    bw.SSID = 'Test SSID 1'
    bw.BeaconType = '11i'
    bw.IEEE11iEncryptionModes = 'AESEncryption'
    bw.KeyPassphrase = 'testpassword'
    bw.SSIDAdvertisementEnabled = False
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    # testdata/binwifi/binwifi quotes every argument
    exp = [
        '"set" "-P" "-b" "2.4" "-e" "WPA2_PSK_AES" "-H" "-c" "10" '
        '"-s" "Test SSID 1" "-a" "HIGH" "-p" "a/b/g/n"',
        'PSK=testpassword'
    ]
    self.assertEqual(buf.strip().splitlines(), exp)

  def test5GhzConfigCommit(self):
    bw = binwifi.WlanConfiguration('wifi0', band='5', width_5g=80)
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = False
    bw.Channel = 44
    bw.X_CATAWAMPUS_ORG_AutoChanType = 'HIGH'
    bw.SSID = 'Test SSID 1'
    bw.BeaconType = '11i'
    bw.IEEE11iEncryptionModes = 'AESEncryption'
    bw.KeyPassphrase = 'testpassword'
    bw.SSIDAdvertisementEnabled = False
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    # testdata/binwifi/binwifi quotes every argument
    exp = [
        '"set" "-P" "-b" "5" "-e" "WPA2_PSK_AES" "-H" "-c" "44" '
        '"-s" "Test SSID 1" "-a" "HIGH" "-w" "80" "-p" "a/b/g/n"',
        'PSK=testpassword'
    ]
    self.assertEqual(buf.strip().splitlines(), exp)

  def testRadioDisabled(self):
    bw = binwifi.WlanConfiguration('wifi0', band='2.4')
    bw.StartTransaction()
    bw.Enable = True
    bw.RadioEnabled = False
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    # testdata/binwifi/binwifi quotes every argument
    exp = ['"off" "-P" "-b" "2.4"', 'PSK=']
    self.assertEqual(buf.strip().splitlines(), exp)

  def testPSK(self):
    for i in range(1, 11):
      bw = binwifi.WlanConfiguration('wifi0', band='2.4')
      bw.StartTransaction()
      bw.RadioEnabled = True
      bw.Enable = True
      bw.AutoChannelEnable = True
      bw.SSID = 'Test SSID 1'
      bw.BeaconType = 'WPAand11i'
      bw.IEEE11iEncryptionModes = 'AESEncryption'
      bw.PreSharedKeyList[str(i)].KeyPassphrase = 'testpassword'
      self.loop.RunOnce(timeout=1)
      buf = open(self.wifioutfile).read()
      # testdata/binwifi/binwifi quotes every argument
      exp = [
          '"set" "-P" "-b" "2.4" "-e" "WPA12_PSK_AES" '
          '"-c" "auto" "-s" "Test SSID 1" "-p" "a/b/g/n"',
          'PSK=testpassword'
      ]
      self.assertEqual(buf.strip().splitlines(), exp)
      os.remove(self.wifioutfile)

  def testPasswordTriggers(self):
    bw = binwifi.WlanConfiguration('wifi0', band='2.4')
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID 1'
    bw.BeaconType = 'WPAand11i'
    bw.IEEE11iEncryptionModes = 'AESEncryption'
    bw.PreSharedKeyList['1'].KeyPassphrase = 'testpassword'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()

    # Test that setting the KeyPassphrase alone is enough to write the config
    bw.PreSharedKeyList['1'].KeyPassphrase = ''
    for i in reversed(range(1, 11)):
      bw.PreSharedKeyList[str(i)].KeyPassphrase = 'testpassword' + str(i)
      self.loop.RunOnce(timeout=1)
      newbuf = open(self.wifioutfile).read()
      self.assertNotEqual(newbuf, buf)
      buf = newbuf

  def testWEP(self):
    bw = binwifi.WlanConfiguration('wifi0', band='2.4')
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID'
    bw.BeaconType = 'Basic'
    bw.BasicEncryptionModes = 'WEPEncryption'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    exp = [
        '"set" "-P" "-b" "2.4" "-e" "WEP" '
        '"-c" "auto" "-s" "Test SSID" "-p" "a/b/g/n"',
        'PSK='
    ]
    self.assertEqual(buf.strip().splitlines(), exp)

  def testSSID(self):
    bw = binwifi.WlanConfiguration('wifi0', band='5')
    bw.StartTransaction()
    bw.SSID = 'this is ok'
    self.loop.RunOnce(timeout=1)
    bw.SSID = '0123456789abcdef0123456789abcdef'  # should still be ok
    self.loop.RunOnce(timeout=1)
    self.assertRaises(ValueError, setattr, bw, 'SSID',
                      '0123456789abcdef0123456789abcdef0')
    self.loop.RunOnce(timeout=1)

  def testAssociatedDevices(self):
    bw = binwifi.WlanConfiguration('wifi0')
    self.assertEqual(bw.TotalAssociations, 3)
    found = 0
    for c in bw.AssociatedDeviceList.values():
      if c.AssociatedDeviceMACAddress == '00:00:01:00:00:01':
        self.assertTrue(c.X_CATAWAMPUS_ORG_Active)
        self.assertEqual(c.X_CATAWAMPUS_ORG_LastDataUplinkRate, 10000)
        self.assertEqual(c.X_CATAWAMPUS_ORG_LastDataDownlinkRate, 11000)
        self.assertEqual(c.LastDataTransmitRate, '11')
        self.assertEqual(c.X_CATAWAMPUS_ORG_SignalStrength, -8)
        self.assertEqual(c.X_CATAWAMPUS_ORG_SignalStrengthAverage, -9)
        found |= 1
      elif c.AssociatedDeviceMACAddress == '00:00:01:00:00:02':
        self.assertTrue(c.X_CATAWAMPUS_ORG_Active)
        self.assertEqual(c.X_CATAWAMPUS_ORG_LastDataUplinkRate, 21000)
        self.assertEqual(c.X_CATAWAMPUS_ORG_LastDataDownlinkRate, 22000)
        self.assertEqual(c.LastDataTransmitRate, '22')
        self.assertEqual(c.X_CATAWAMPUS_ORG_SignalStrength, -19)
        self.assertEqual(c.X_CATAWAMPUS_ORG_SignalStrengthAverage, -20)
        found |= 2
      elif c.AssociatedDeviceMACAddress == '00:00:01:00:00:03':
        self.assertFalse(c.X_CATAWAMPUS_ORG_Active)
        self.assertEqual(c.X_CATAWAMPUS_ORG_LastDataUplinkRate, 32000)
        self.assertEqual(c.X_CATAWAMPUS_ORG_LastDataDownlinkRate, 33000)
        self.assertEqual(c.LastDataTransmitRate, '33')
        self.assertEqual(c.X_CATAWAMPUS_ORG_SignalStrength, -30)
        self.assertEqual(c.X_CATAWAMPUS_ORG_SignalStrengthAverage, -31)
        found |= 4
    self.assertEqual(found, 0x7)

  def testConfigNotChanged(self):
    bw = binwifi.WlanConfiguration('wifi0', band='5')
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = False
    bw.Channel = 44
    bw.SSID = 'Test SSID'
    bw.BeaconType = 'Basic'
    self.loop.RunOnce(timeout=1)
    self.assertTrue(os.path.exists(self.wifioutfile))
    os.unlink(self.wifioutfile)
    # Make no actual change in the object, /bin/wifi should not be run again.
    bw.StartTransaction()
    bw.Channel = 44
    self.loop.RunOnce(timeout=1)
    self.assertFalse(os.path.exists(self.wifioutfile))

  def testVariousOperatingFrequencyBand(self):
    bw = binwifi.WlanConfiguration('wifi0')
    self.assertEqual(bw.OperatingFrequencyBand, '5GHz')
    bw.OperatingFrequencyBand = '2.4GHz'
    self.assertEqual(bw.OperatingFrequencyBand, '2.4GHz')
    bw.OperatingFrequencyBand = ''
    self.assertEqual(bw.OperatingFrequencyBand, '5GHz')
    self.assertRaises(ValueError, setattr, bw,
                      'OperatingFrequencyBand', '60GHz')
    self.loop.RunOnce(timeout=1)

  def testOperatingFrequencyBand(self):
    bw = binwifi.WlanConfiguration('wifi0')
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.OperatingFrequencyBand = '5GHz'
    bw.SSID = 'Test SSID'
    bw.BeaconType = 'Basic'
    bw.BasicEncryptionModes = 'None'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    self.assertTrue('"-b" "5"' in buf)

    bw.OperatingFrequencyBand = '2.4GHz'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    self.assertTrue('"-b" "2.4"' in buf)

  def testBeaconType(self):
    bw = binwifi.WlanConfiguration('wifi0', band='5')
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = False
    bw.Channel = 44
    bw.X_CATAWAMPUS_ORG_AutoChanType = 'HIGH'
    bw.SSID = 'SSID'
    bw.BeaconType = '11i'
    bw.IEEE11iEncryptionModes = 'AESEncryption'
    bw.KeyPassphrase = 'testpassword'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    self.assertTrue('WPA2_PSK_AES' in buf)
    bw.BeaconType = 'WPA'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    self.assertTrue('WPA_PSK_AES' in buf)
    bw.BeaconType = 'WPAand11i'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    self.assertTrue('WPA12_PSK_AES' in buf)

  def testStandard(self):
    bw = binwifi.WlanConfiguration('wifi0', band='5', width_5g=80)
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = False
    bw.Channel = 44
    bw.X_CATAWAMPUS_ORG_AutoChanType = 'HIGH'
    bw.SSID = 'Test SSID 1'
    bw.BeaconType = '11i'
    bw.IEEE11iEncryptionModes = 'AESEncryption'
    bw.KeyPassphrase = 'testpassword'
    bw.SSIDAdvertisementEnabled = False

    bw.Standard = 'ac'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    self.assertTrue('"-p" "a/b/g/n/ac"' in buf)

    bw.Standard = 'n'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    self.assertTrue('"-p" "a/b/g/n"' in buf)

    bw.Standard = 'g'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    self.assertTrue('"-p" "a/b/g"' in buf)

    bw.Standard = 'b'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    # We set 'a/b' and expect OperatingFrequencyBand to determine the band.
    self.assertTrue('"-p" "a/b"' in buf)

    bw.Standard = 'a'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    # We set 'a/b' and expect OperatingFrequencyBand to determine the band.
    self.assertTrue('"-p" "a/b"' in buf)

  def testWidth(self):
    bw = binwifi.WlanConfiguration('wifi0', band='5', width_5g=80)
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID 1'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    self.assertTrue('"-w" "80"' in buf)

    bw = binwifi.WlanConfiguration('wifi0', band='5', width_2_4g=80)
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID 1'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    self.assertFalse('"-w" "80"' in buf)

    bw = binwifi.WlanConfiguration('wifi0', band='2.4', width_2_4g=80)
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID 1'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    self.assertTrue('"-w" "80"' in buf)

    bw = binwifi.WlanConfiguration('wifi0', band='2.4', width_5g=80)
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID 1'
    self.loop.RunOnce(timeout=1)
    buf = open(self.wifioutfile).read()
    self.assertFalse('"-w" "80"' in buf)


if __name__ == '__main__':
  unittest.main()

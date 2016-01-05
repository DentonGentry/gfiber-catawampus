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

import json
import os
import shutil
import tempfile
import time

import google3
import binwifi
import netdev
import tr.handle
import tr.session
from tr.wvtest import unittest

BRIDGE_PARAMS = [
    ('', ' "--bridge="'),
    ('br0', ' "--bridge=br0"'),
    ('br1', ' "--bridge=br1"'),
]

SUFFIX_PARAMS = [
    ('', ''),
    ('portal', ' "-S" "portal"'),
]


class BinWifiTest(unittest.TestCase):

  def setUp(self):
    self.old_BINWIFI = binwifi.BINWIFI
    self.old_IS_WIRELESS_CLIENT = binwifi.IS_WIRELESS_CLIENT
    binwifi.IS_WIRELESS_CLIENT[0] = 'testdata/binwifi/is-wireless-client'
    self.tmpdir = tempfile.mkdtemp()
    self.wifioutfile = os.path.join(self.tmpdir, 'wifi.out')
    binwifi.BINWIFI = ['testdata/binwifi/binwifi', self.wifioutfile]
    self.old_PROC_NET_DEV = netdev.PROC_NET_DEV
    netdev.PROC_NET_DEV = 'testdata/binwifi/proc_net_dev'
    self.old_CONMAN_DIR = binwifi.CONMAN_DIR[0]
    binwifi.CONMAN_DIR[0] = os.path.join(self.tmpdir, 'conman')
    self.old_STATIONS_DIR = binwifi.STATIONS_DIR[0]
    binwifi.STATIONS_DIR[0] = os.path.join(self.tmpdir, 'stations')
    self.old_TMPWAVEGUIDE = binwifi.TMPWAVEGUIDE[0]
    binwifi.TMPWAVEGUIDE[0] = self.tmpdir
    self.old_WIFIINFO_DIR = binwifi.WIFIINFO_DIR[0]
    binwifi.WIFIINFO_DIR[0] = 'testdata/binwifi'
    self.loop = tr.mainloop.MainLoop()
    tr.session.cache.flush()
    self.bw_pool = []

  def tearDown(self):
    binwifi.BINWIFI = self.old_BINWIFI
    binwifi.IS_WIRELESS_CLIENT = self.old_IS_WIRELESS_CLIENT
    netdev.PROC_NET_DEV = self.old_PROC_NET_DEV
    binwifi.CONMAN_DIR[0] = self.old_CONMAN_DIR
    binwifi.STATIONS_DIR[0] = self.old_STATIONS_DIR
    binwifi.TMPWAVEGUIDE[0] = self.old_TMPWAVEGUIDE
    binwifi.WIFIINFO_DIR[0] = self.old_WIFIINFO_DIR
    shutil.rmtree(self.tmpdir)
    # Let any pending callbacks expire
    self.loop.RunOnce(timeout=1)
    for bw in self.bw_pool:
      bw.release()

  def GatherOutput(self):
    self.loop.RunOnce(timeout=1)
    with open(self.wifioutfile, 'r+') as of:
      buf = of.read()
      of.truncate(0)
    return buf

  def WlanConfiguration(self, *args, **kwargs):
    """Create WlanConfiguration objects in a pool that we release each test."""
    bw = binwifi.WlanConfiguration(*args, **kwargs)
    self.bw_pool.append(bw)
    return bw

  def testValidateExports(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0')
    tr.handle.ValidateExports(bw)

  def testCorrectParentModel(self):
    # We want the catawampus extension, not the base tr-98 model.
    bw = self.WlanConfiguration('wifi0', '', 'br0')
    self.assertTrue(tr.handle.Handle.IsValidExport(
        bw, 'OperatingFrequencyBand'))

  def testWEPKeyIndex(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0')
    bw.StartTransaction()
    bw.WEPKeyIndex = 1  # should succeed
    bw.WEPKeyIndex = 2
    bw.WEPKeyIndex = 3
    bw.WEPKeyIndex = 4
    self.assertRaises(ValueError, setattr, bw, 'WEPKeyIndex', 0)
    self.assertRaises(ValueError, setattr, bw, 'WEPKeyIndex', 5)

  def testWifiStats(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0')
    self.assertEqual(bw.TotalBytesReceived, 1)
    self.assertEqual(bw.TotalBytesSent, 9)
    self.assertEqual(bw.TotalPacketsReceived, 100)
    self.assertEqual(bw.TotalPacketsSent, 10)
    self.assertEqual(bw.Stats.UnicastPacketsSent, 10)

  def testConfigCommit(self):
    for (if_suffix, s_param) in SUFFIX_PARAMS:
      for (bridge, b_param) in BRIDGE_PARAMS:
        bw = self.WlanConfiguration('wifi0', if_suffix, bridge, band='2.4')
        bw.StartTransaction()
        bw.RadioEnabled = True
        bw.Enable = True
        bw.AutoChannelEnable = True
        bw.X_CATAWAMPUS_ORG_AutoChanType = 'HIGH'
        bw.SSID = 'Test SSID 1'
        bw.BeaconType = 'WPA'
        bw.IEEE11iEncryptionModes = 'AESEncryption'
        bw.KeyPassphrase = 'testpassword'
        buf = self.GatherOutput()
        # testdata/binwifi/binwifi quotes every argument
        exp = [
            '"set" "-P" "-b" "2.4" "-e" "WPA_PSK_AES"%s%s "-c" "auto" "-s" '
            '"Test SSID 1" "-a" "HIGH" "-p" "a/b/g/n" '
            '"-M"' % (s_param, b_param),
            'PSK=testpassword'
        ]
        self.assertEqual(buf.strip().splitlines(), exp)

  def testAnotherConfigCommit(self):
    for (if_suffix, s_param) in SUFFIX_PARAMS:
      for (bridge, b_param) in BRIDGE_PARAMS:
        bw = self.WlanConfiguration('wlan2', if_suffix, bridge, band='2.4')
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
        buf = self.GatherOutput()
        # testdata/binwifi/binwifi quotes every argument
        exp = [
            '"set" "-P" "-b" "2.4" "-e" "WPA2_PSK_AES"%s%s "-H" "-c" "10" '
            '"-s" "Test SSID 1" "-a" "HIGH" "-p" "a/b/g/n" "-M"'
            % (s_param, b_param),
            'PSK=testpassword'
        ]
        self.assertEqual(buf.strip().splitlines(), exp)

  def test5GhzConfigCommit(self):
    for (if_suffix, s_param) in SUFFIX_PARAMS:
      for (bridge, b_param) in BRIDGE_PARAMS:
        bw = self.WlanConfiguration(
            'wifi0', if_suffix, bridge, band='5', width_5g=80)
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
        buf = self.GatherOutput()
        # testdata/binwifi/binwifi quotes every argument
        exp = [
            '"set" "-P" "-b" "5" "-e" "WPA2_PSK_AES"%s%s "-H" "-c" "44" '
            '"-s" "Test SSID 1" "-a" "HIGH" "-w" "80" "-p" "a/b/g/n" "-M"'
            % (s_param, b_param),
            'PSK=testpassword'
        ]
        self.assertEqual(buf.strip().splitlines(), exp)

  def testRadioDisabled(self):
    for (if_suffix, s_param) in SUFFIX_PARAMS:
      bw = self.WlanConfiguration('wifi0', if_suffix, 'br1', band='2.4')
      # The radio will only be disabled by command if it is first enabled.
      bw.StartTransaction()
      bw.Enable = True
      bw.RadioEnabled = True
      _ = self.GatherOutput()

      bw.RadioEnabled = False
      buf = self.GatherOutput()
      # testdata/binwifi/binwifi quotes every argument
      exp = ['"stopap" "-P" "-b" "2.4"%s' % s_param, 'PSK=']
      self.assertEqual(buf.strip().splitlines(), exp)

  def testClientConfig(self):
    bw = self.WlanConfiguration('wcli0', '', '')
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.ClientEnable = True
    bw.SSID = 'Test SSID 2'
    bw.KeyPassphrase = 'testpassword'
    buf = self.GatherOutput()
    exp = ['"setclient" "-P" "-s" "Test SSID 2"', 'CLIENT_PSK=testpassword']
    self.assertEqual(buf.strip().splitlines(), exp)

    bw.RadioEnabled = False
    buf = self.GatherOutput()
    # testdata/binwifi/binwifi quotes every argument
    exp = ['"stopclient" "-P" "-b" "5"', 'PSK=']
    self.assertEqual(buf.strip().splitlines(), exp)

  def testUpdateBinWifi(self):
    def Verbs(buf):
      verbs = []
      for line in buf.strip().splitlines()[::2]:  # don't care about environment
        verbs.append(line.split()[0])

      return verbs

    bw = self.WlanConfiguration('wlan0', '', 'br0', band='2.4')
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.SSID = 'Test SSID 2'
    bw.KeyPassphrase = 'testpassword'
    buf = self.GatherOutput()
    self.assertEqual(Verbs(buf), ['"set"'])

    bw.ClientEnable = True
    buf = self.GatherOutput()
    self.assertEqual(Verbs(buf), ['"setclient"', '"set"'])

    bw.Enable = False
    buf = self.GatherOutput()
    self.assertEqual(Verbs(buf), ['"setclient"', '"stopap"'])

    bw.ClientEnable = False
    buf = self.GatherOutput()
    self.assertEqual(Verbs(buf), ['"stopclient"'])

    bw.Enable = True
    bw.ClientEnable = True
    buf = self.GatherOutput()
    self.assertEqual(Verbs(buf), ['"setclient"', '"set"'])

    bw.SSID = 'Test SSID 2A'
    buf = self.GatherOutput()
    self.assertEqual(Verbs(buf), ['"setclient"', '"set"'])

    bw.Enable = False
    bw.ClientEnable = False
    buf = self.GatherOutput()
    self.assertEqual(Verbs(buf), ['"stopclient"', '"stopap"'])

  def testWifiCmdFile(self):
    def loadWifiCmdFile(basename):
      fullpath = os.path.join(binwifi.CONMAN_DIR[0], basename)
      with open(fullpath) as cmdfile:
        return json.load(cmdfile)

    bw = self.WlanConfiguration('wlan1', '', 'br0', band='5')
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.SSID = 'Test Wifi Cmd SSID 5'
    bw.KeyPassphrase = 'testpassword'
    self.GatherOutput()

    self.assertEqual(sorted(os.listdir(binwifi.CONMAN_DIR[0])),
                     ['wlan_configuration.5.json'])

    wc5 = loadWifiCmdFile('wlan_configuration.5.json')
    self.assertTrue(wc5['access_point'])

    # Deliberately create a WlanConfiguration outside of the pool, so we can
    # release it early and test that it cleans up its command file.
    bw24 = binwifi.WlanConfiguration('wlan0', '', 'br0', band='2.4')
    bw24.StartTransaction()
    bw24.RadioEnabled = True
    bw24.Enable = True
    bw24.SSID = 'Test Wifi Cmd SSID 2.4'
    bw24.KeyPassphrase = 'testpassword'

    bw.Enable = False
    self.GatherOutput()

    self.assertEqual(sorted(os.listdir(binwifi.CONMAN_DIR[0])),
                     ['wlan_configuration.2.4.json',
                      'wlan_configuration.5.json'])

    wc24 = loadWifiCmdFile('wlan_configuration.2.4.json')
    self.assertTrue(wc24['access_point'])
    self.assertEqual(wc24['command'],
                     binwifi.BINWIFI + [u'set', u'-P', u'-b', u'2.4', u'-e',
                                        u'WPA2_PSK_AES', u'--bridge=br0', u'-c',
                                        u'auto', u'-s',
                                        u'Test Wifi Cmd SSID 2.4', u'-p',
                                        u'a/b/g/n', u'-M'])

    wc5 = loadWifiCmdFile('wlan_configuration.5.json')
    self.assertFalse(wc5['access_point'])
    self.assertEqual(wc5['command'],
                     binwifi.BINWIFI + [u'set', u'-P', u'-b', u'5', u'-e',
                                        u'WPA2_PSK_AES', u'--bridge=br0', u'-c',
                                        u'auto', u'-s', u'Test Wifi Cmd SSID 5',
                                        u'-p', u'a/b/g/n', u'-M'])

    bw24.release()
    self.assertEqual(sorted(os.listdir(binwifi.CONMAN_DIR[0])),
                     ['wlan_configuration.5.json'])

    bw.Enable = True
    self.GatherOutput()
    wc5 = loadWifiCmdFile('wlan_configuration.5.json')
    self.assertTrue(wc5['access_point'])

    bw_portal = self.WlanConfiguration('wlan1', '_portal', 'br1', band='5')
    bw_portal.StartTransaction()
    bw_portal.RadioEnabled = True
    bw_portal.Enable = True
    bw_portal.SSID = 'GFiberSetup'

    self.GatherOutput()
    self.assertEqual(sorted(os.listdir(binwifi.CONMAN_DIR[0])),
                     ['wlan_configuration.5.json',
                      'wlan_configuration_portal.5.json'])

  def testPSK(self):
    for i in range(1, 11):
      for (if_suffix, s_param) in SUFFIX_PARAMS:
        for (bridge, b_param) in BRIDGE_PARAMS:
          bw = self.WlanConfiguration(
              'wifi0', if_suffix, bridge, band='2.4')
          bw.StartTransaction()
          bw.RadioEnabled = True
          bw.Enable = True
          bw.AutoChannelEnable = True
          bw.SSID = 'Test SSID 1'
          bw.BeaconType = 'WPAand11i'
          bw.IEEE11iEncryptionModes = 'AESEncryption'
          bw.PreSharedKeyList[str(i)].KeyPassphrase = 'testpassword'
          buf = self.GatherOutput()
          # testdata/binwifi/binwifi quotes every argument
          exp = [
              '"set" "-P" "-b" "2.4" "-e" "WPA12_PSK_AES"%s%s '
              '"-c" "auto" "-s" "Test SSID 1" "-p" "a/b/g/n" "-M"'
              % (s_param, b_param),
              'PSK=testpassword'
          ]
          self.assertEqual(buf.strip().splitlines(), exp)

  def testPasswordTriggers(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0', band='2.4')
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID 1'
    bw.BeaconType = 'WPAand11i'
    bw.IEEE11iEncryptionModes = 'AESEncryption'
    bw.PreSharedKeyList['1'].KeyPassphrase = 'testpassword'
    buf = self.GatherOutput()

    # Test that setting the KeyPassphrase alone is enough to write the config
    bw.PreSharedKeyList['1'].KeyPassphrase = ''
    for i in reversed(range(1, 11)):
      bw.PreSharedKeyList[str(i)].KeyPassphrase = 'testpassword' + str(i)
      newbuf = self.GatherOutput()
      self.assertNotEqual(newbuf, buf)
      buf = newbuf

  def testWEP(self):
    for (if_suffix, s_param) in SUFFIX_PARAMS:
      for (bridge, b_param) in BRIDGE_PARAMS:
        bw = self.WlanConfiguration(
            'wifi0', if_suffix, bridge, band='2.4')
        bw.StartTransaction()
        bw.RadioEnabled = True
        bw.Enable = True
        bw.AutoChannelEnable = True
        bw.SSID = 'Test SSID'
        bw.BeaconType = 'Basic'
        bw.BasicEncryptionModes = 'WEPEncryption'
        buf = self.GatherOutput()
        exp = [
            '"set" "-P" "-b" "2.4" "-e" "WEP"%s%s '
            '"-c" "auto" "-s" "Test SSID" "-p" "a/b/g/n" '
            '"-M"' % (s_param, b_param),
            'PSK='
        ]
        self.assertEqual(buf.strip().splitlines(), exp)

  def testSSID(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0', band='5')
    bw.StartTransaction()
    bw.SSID = 'this is ok'
    self.loop.RunOnce(timeout=1)
    bw.SSID = '0123456789abcdef0123456789abcdef'  # should still be ok
    self.loop.RunOnce(timeout=1)
    self.assertRaises(ValueError, setattr, bw, 'SSID',
                      '0123456789abcdef0123456789abcdef0')
    self.loop.RunOnce(timeout=1)

  # TODO(theannielin): Consume data from mocked /bin/wifi in this test
  def testAssociatedDevices(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0')
    stations = {'00:00:01:00:00:01': {'inactive since': 900,
                                      'authenticated': 'yes',
                                      'tx packets': 5,
                                      'tx failed': 7,
                                      'tx bitrate': 10.0,
                                      'rx packets': 3,
                                      'rx bitrate': 11.0,
                                      'tx bytes': 4,
                                      'tx retries': 6,
                                      'rx bytes': 2,
                                      'signal': -8,
                                      'signal avg': -9,
                                      'authorized': 'yes',
                                      'ifname': 'wifi0'},
                '00:00:01:00:00:02': {'inactive since': 1000,
                                      'authenticated': 'yes',
                                      'tx packets': 16,
                                      'tx failed': 18,
                                      'tx bitrate': 21.0,
                                      'rx packets': 14,
                                      'rx bitrate': 22.0,
                                      'tx bytes': 15,
                                      'tx retries': 17,
                                      'rx bytes': 13,
                                      'signal': -19,
                                      'signal avg': -20,
                                      'authorized': 'yes',
                                      'ifname': 'wifi0'},
                '00:00:01:00:00:03': {'inactive since': 500,
                                      'authenticated': 'yes',
                                      'tx packets': 27,
                                      'tx failed': 29,
                                      'tx bitrate': 32.0,
                                      'rx packets': 25,
                                      'rx bitrate': 33.0,
                                      'tx bytes': 26,
                                      'tx retries': 28,
                                      'rx bytes': 24,
                                      'signal': -30,
                                      'signal avg': -31,
                                      'authorized': 'yes',
                                      'ifname': 'wifi0'}}
    time.time = lambda: 1000  # return 1000 in binwifi to make testing easier
    for mac_addr in stations:
      with open(os.path.join(binwifi.STATIONS_DIR[0], mac_addr), 'w') as f:
        f.write(json.dumps(stations[mac_addr]))
    bw.AssocDeviceListMaker()
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

  def testVariousOperatingFrequencyBand(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0')
    self.assertEqual(bw.OperatingFrequencyBand, '5GHz')
    bw.OperatingFrequencyBand = '2.4GHz'
    self.assertEqual(bw.OperatingFrequencyBand, '2.4GHz')
    bw.OperatingFrequencyBand = ''
    self.assertEqual(bw.OperatingFrequencyBand, '5GHz')
    self.assertRaises(ValueError, setattr, bw,
                      'OperatingFrequencyBand', '60GHz')
    self.loop.RunOnce(timeout=1)

  def testOperatingFrequencyBand(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0')
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.OperatingFrequencyBand = '5GHz'
    bw.SSID = 'Test SSID'
    bw.BeaconType = 'Basic'
    bw.BasicEncryptionModes = 'None'
    buf = self.GatherOutput()
    self.assertTrue('"-b" "5"' in buf)

    bw.OperatingFrequencyBand = '2.4GHz'
    buf = self.GatherOutput()
    self.assertTrue('"-b" "2.4"' in buf)

  def testBeaconType(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0', band='5')
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
    buf = self.GatherOutput()
    self.assertTrue('WPA2_PSK_AES' in buf)
    bw.BeaconType = 'WPA'
    buf = self.GatherOutput()
    self.assertTrue('WPA_PSK_AES' in buf)
    bw.BeaconType = 'WPAand11i'
    buf = self.GatherOutput()
    self.assertTrue('WPA12_PSK_AES' in buf)

  def testStandard(self):
    bw = self.WlanConfiguration(
        'wifi0', '', 'br0', band='5', width_5g=80)
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
    bw.GuardInterval = '800nsec'
    bw.RekeyingInterval = 3600
    bw.WMMEnable = False

    bw.Standard = 'ac'
    buf = self.GatherOutput()
    self.assertTrue('"-p" "a/b/g/n/ac"' in buf)
    self.assertTrue('"-M"' in buf)  # always enabled for n/ac modes
    self.assertTrue('"-G"' not in buf)

    bw.GuardInterval = '400nsec'
    buf = self.GatherOutput()
    self.assertTrue('"-G"' in buf)
    self.assertTrue('"-Y"' not in buf)
    self.assertTrue('"-X"' not in buf)
    self.assertTrue('"-XX"' not in buf)

    bw.RekeyingInterval = 0
    buf = self.GatherOutput()
    self.assertTrue('"-Y"' in buf)
    self.assertTrue('"-X"' not in buf)
    self.assertTrue('"-XX"' not in buf)

    bw.RekeyingInterval = 1
    buf = self.GatherOutput()
    self.assertTrue('"-Y"' not in buf)
    self.assertTrue('"-X"' in buf)
    self.assertTrue('"-XX"' not in buf)

    bw.RekeyingInterval = 10
    buf = self.GatherOutput()
    self.assertTrue('"-Y"' not in buf)
    self.assertTrue('"-X"' not in buf)
    self.assertTrue('"-XX"' in buf)

    bw.Standard = 'n'
    buf = self.GatherOutput()
    self.assertTrue('"-p" "a/b/g/n"' in buf)
    self.assertTrue('"-M"' in buf)  # always enabled for n/ac modes

    bw.Standard = 'g'
    buf = self.GatherOutput()
    self.assertTrue('"-p" "a/b/g"' in buf)
    self.assertTrue('"-M"' not in buf)  # not auto-enabled

    bw.WMMEnable = True
    buf = self.GatherOutput()
    self.assertTrue('"-M"' in buf)

    bw.Standard = 'b'
    buf = self.GatherOutput()
    # We set 'a/b' and expect OperatingFrequencyBand to determine the band.
    self.assertTrue('"-p" "a/b"' in buf)

    bw.Standard = 'a'
    buf = self.GatherOutput()
    # No output, because 'a' is the same as the previous 'b', so wifi doesn't
    # need to restart.
    self.assertEqual(buf, '')

    bw.Standard = 'g'
    buf = self.GatherOutput()
    bw.Standard = 'a'
    buf = self.GatherOutput()
    # Same output as 'b'
    self.assertTrue('"-p" "a/b"' in buf)

  def testWidth(self):
    bw = self.WlanConfiguration(
        'wifi0', '', 'br0', band='5', width_5g=80)
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID 1'
    buf = self.GatherOutput()
    self.assertTrue('"-w" "80"' in buf)

    bw = self.WlanConfiguration(
        'wifi0', '', 'br0', band='5', width_2_4g=40)
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID 1'
    buf = self.GatherOutput()
    self.assertFalse('"-w" "40"' in buf)

    bw = self.WlanConfiguration(
        'wifi0', '', 'br0', band='2.4', width_2_4g=40)
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID 1'
    buf = self.GatherOutput()
    self.assertTrue('"-w" "40"' in buf)

    bw = self.WlanConfiguration(
        'wifi0', '', 'br0', band='2.4', width_5g=80)
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID 1'
    buf = self.GatherOutput()
    self.assertFalse('"-w" "80"' in buf)

  def testAutoDisableRecommended(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0', band='5')
    self.assertFalse(bw.X_CATAWAMPUS_ORG_AutoDisableRecommended)
    open(self.tmpdir + '/wifi0.disabled', 'w').write('')
    self.assertTrue(bw.X_CATAWAMPUS_ORG_AutoDisableRecommended)
    open(self.tmpdir + '/wifi0.disabled', 'w').write('f8:8f:ca:00:00:01')
    self.assertTrue(bw.X_CATAWAMPUS_ORG_AutoDisableRecommended)


if __name__ == '__main__':
  unittest.main()

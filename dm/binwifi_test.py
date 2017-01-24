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
import shlex
import shutil
import tempfile

import google3
import binwifi
import netdev
import platform.gfmedia.device as device
import tr.handle
import tr.session
from tr.wvtest import unittest

BRIDGE_PARAMS = [
    ('', '--bridge='),
    ('br0', '--bridge=br0'),
    ('br1', '--bridge=br1'),
]

SUFFIX_PARAMS = [
    ('', ''),
    ('_portal', '--interface-suffix=_portal'),
]


class BinWifiTest(unittest.TestCase):

  def setUp(self):
    self.old_BINWIFI = binwifi.BINWIFI
    binwifi.BINWIFI = ['testdata/binwifi/binwifi']
    self.tmpdir = tempfile.mkdtemp()
    self.old_PROC_NET_DEV = netdev.PROC_NET_DEV
    netdev.PROC_NET_DEV = 'testdata/binwifi/proc_net_dev'
    self.old_CONMAN_DIR = binwifi.CONMAN_DIR[0]
    binwifi.CONMAN_DIR[0] = os.path.join(self.tmpdir, 'conman')
    self.old_CONMAN_TMP_DIR = binwifi.CONMAN_TMP_DIR[0]
    binwifi.CONMAN_TMP_DIR[0] = os.path.join(self.tmpdir, 'conman_tmp')
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
    # Let any pending callbacks expire
    self.loop.RunOnce(timeout=1)
    for bw in self.bw_pool:
      bw.release()

    binwifi.BINWIFI = self.old_BINWIFI
    netdev.PROC_NET_DEV = self.old_PROC_NET_DEV
    binwifi.CONMAN_DIR[0] = self.old_CONMAN_DIR
    binwifi.CONMAN_TMP_DIR[0] = self.old_CONMAN_TMP_DIR
    binwifi.STATIONS_DIR[0] = self.old_STATIONS_DIR
    binwifi.TMPWAVEGUIDE[0] = self.old_TMPWAVEGUIDE
    binwifi.WIFIINFO_DIR[0] = self.old_WIFIINFO_DIR
    shutil.rmtree(self.tmpdir)

  def GatherOutput(self, wlan_configuration):
    self.loop.RunOnce(timeout=1)
    command = None
    command_filename = wlan_configuration.WifiCommandFileName()
    if os.path.exists(command_filename):
      with open(command_filename, 'r+') as of:
        command = of.read()
        of.truncate(0)

    ap_enabled = os.path.exists(wlan_configuration.APEnabledFileName())

    return ap_enabled, command

  def WlanConfiguration(self, *args, **kwargs):
    """Create WlanConfiguration objects in a pool that we release each test."""
    bw = binwifi.WlanConfiguration(*args, **kwargs)
    self.bw_pool.append(bw)
    return bw

  def testValidateExports(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0', device.Radio())
    tr.handle.ValidateExports(bw)

  def testCorrectParentModel(self):
    # We want the catawampus extension, not the base tr-98 model.
    bw = self.WlanConfiguration('wifi0', '', 'br0', device.Radio())
    self.assertTrue(tr.handle.Handle.IsValidExport(
        bw, 'OperatingFrequencyBand'))

  def testWEPKeyIndex(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0', device.Radio())
    bw.StartTransaction()
    bw.WEPKeyIndex = 1  # should succeed
    bw.WEPKeyIndex = 2
    bw.WEPKeyIndex = 3
    bw.WEPKeyIndex = 4
    self.assertRaises(ValueError, setattr, bw, 'WEPKeyIndex', 0)
    self.assertRaises(ValueError, setattr, bw, 'WEPKeyIndex', 5)

  def testWifiStats(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0', device.Radio())
    self.assertEqual(bw.TotalBytesReceived, 1)
    self.assertEqual(bw.TotalBytesSent, 9)
    self.assertEqual(bw.TotalPacketsReceived, 100)
    self.assertEqual(bw.TotalPacketsSent, 10)
    self.assertEqual(bw.Stats.UnicastPacketsSent, 10)

  def testConfigCommit(self):
    for (if_suffix, s_param) in SUFFIX_PARAMS:
      for (bridge, b_param) in BRIDGE_PARAMS:
        bw = self.WlanConfiguration('wifi0', if_suffix, bridge, device.Radio(),
                                    band='2.4')
        bw.StartTransaction()
        bw.RadioEnabled = True
        bw.Enable = True
        bw.AutoChannelEnable = True
        bw.X_CATAWAMPUS_ORG_AutoChanType = 'HIGH'
        bw.SSID = 'Test SSID 1'
        bw.BeaconType = 'WPA'
        bw.IEEE11iEncryptionModes = 'AESEncryption'
        bw.KeyPassphrase = 'testpassword'
        ap, buf = self.GatherOutput(bw)
        exp = [
            'env', 'WIFI_PSK=testpassword', binwifi.BINWIFI[0],
            'set', '-P', '-b', '2.4', '-e', 'WPA_PSK_AES', s_param, b_param,
            '-c', 'auto', '-s', 'Test SSID 1', '-a', 'HIGH', '-p', 'a/b/g/n',
            '-M',
        ]

        self.assertTrue(ap)
        self.assertEqual(buf.strip().splitlines(), [l for l in exp if l])

  def testAnotherConfigCommit(self):
    for (if_suffix, s_param) in SUFFIX_PARAMS:
      for (bridge, b_param) in BRIDGE_PARAMS:
        bw = self.WlanConfiguration('wlan2', if_suffix, bridge, device.Radio(),
                                    band='2.4')
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
        ap, buf = self.GatherOutput(bw)
        exp = [
            'env', 'WIFI_PSK=testpassword', binwifi.BINWIFI[0],
            'set', '-P', '-b', '2.4', '-e', 'WPA2_PSK_AES', s_param, b_param,
            '-H', '-c', '10', '-s', 'Test SSID 1', '-a', 'HIGH', '-p',
            'a/b/g/n', '-M',
        ]
        self.assertTrue(ap)
        self.assertEqual(buf.strip().splitlines(), [l for l in exp if l])

  def test5GhzConfigCommit(self):
    for (if_suffix, s_param) in SUFFIX_PARAMS:
      for (bridge, b_param) in BRIDGE_PARAMS:
        bw = self.WlanConfiguration(
            'wifi0', if_suffix, bridge, device.Radio(), band='5', width_5g=80)
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
        ap, buf = self.GatherOutput(bw)
        exp = [
            'env', 'WIFI_PSK=testpassword', binwifi.BINWIFI[0],
            'set', '-P', '-b', '5', '-e', 'WPA2_PSK_AES', s_param, b_param,
            '-H', '-c', '44', '-s', 'Test SSID 1', '-a', 'HIGH', '-w', '80',
            '-p', 'a/b/g/n', '-M',
        ]
        self.assertTrue(ap)
        self.assertEqual(buf.strip().splitlines(), [l for l in exp if l])

  def testRadioDisabled(self):
    for if_suffix, s_param in SUFFIX_PARAMS:
      bw = self.WlanConfiguration('wifi0', if_suffix, 'br1', device.Radio(),
                                  band='2.4')
      # The radio will only be disabled by command if it is first enabled.
      bw.StartTransaction()
      bw.Enable = True
      bw.RadioEnabled = True
      bw.SSID = 'Test SSID 1'
      bw.KeyPassphrase = 'testpassword'
      _ = self.GatherOutput(bw)

      bw.RadioEnabled = False
      ap, buf = self.GatherOutput(bw)
      exp = [
          'env', 'WIFI_PSK=testpassword', binwifi.BINWIFI[0],
          'set', '-P', '-b', '2.4', '-e', 'WPA2_PSK_AES', s_param,
          '--bridge=br1', '-c', 'auto', '-s', 'Test SSID 1',
          '-p', 'a/b/g/n', '-M',
      ]
      self.assertFalse(ap)
      self.assertEqual(buf.strip().splitlines(), [l for l in exp if l])

  def testChannelShared(self):
    radio = device.Radio()
    bw = self.WlanConfiguration('wifi0', '', 'br0', radio, band='2.4')
    bw_portal = self.WlanConfiguration('wifi0', '_portal', 'br0', radio,
                                       band='2.4')

    # Set up the captive portal with no specified channel.
    bw_portal.StartTransaction()
    bw_portal.RadioEnabled = True
    bw_portal.Enable = True
    bw_portal.AutoChannelEnable = False
    bw_portal.SSID = 'Portal SSID 1'
    bw_portal.BeaconType = 'WPA'
    bw_portal.IEEE11iEncryptionModes = 'AESEncryption'
    bw_portal.KeyPassphrase = 'testpassword'
    ap, buf = self.GatherOutput(bw_portal)
    exp = [
        'env', 'WIFI_PSK=testpassword', binwifi.BINWIFI[0],
        'set', '-P', '-b', '2.4', '-e', 'WPA_PSK_AES',
        '--interface-suffix=_portal', '--bridge=br0',
        '-s', 'Portal SSID 1', '-p', 'a/b/g/n', '-M',
    ]
    self.assertTrue(ap)
    self.assertEqual(buf.strip().splitlines(), [l for l in exp if l])

    # Now set up the WLAN with a specified channel.  Make sure the specified
    # channel is applied to the captive portal on the same radio as well.
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = False
    bw.Channel = '44'
    bw.SSID = 'Test SSID 1'
    bw.BeaconType = 'WPA'
    bw.IEEE11iEncryptionModes = 'AESEncryption'
    bw.KeyPassphrase = 'testpassword'
    ap, buf = self.GatherOutput(bw)
    exp = [
        'env', 'WIFI_PSK=testpassword', binwifi.BINWIFI[0],
        'set', '-P', '-b', '2.4', '-e', 'WPA_PSK_AES', '', '--bridge=br0',
        '-c', '44', '-s', 'Test SSID 1', '-p', 'a/b/g/n', '-M',
    ]
    self.assertTrue(ap)
    self.assertEqual(buf.strip().splitlines(), [l for l in exp if l])

    ap, buf = self.GatherOutput(bw_portal)
    exp = [
        'env', 'WIFI_PSK=testpassword', binwifi.BINWIFI[0],
        'set', '-P', '-b', '2.4', '-e', 'WPA_PSK_AES',
        '--interface-suffix=_portal', '--bridge=br0',
        '-c', '44', '-s', 'Portal SSID 1', '-p', 'a/b/g/n', '-M',
    ]
    self.assertTrue(ap)
    self.assertEqual(buf.strip().splitlines(), [l for l in exp if l])

  def testPSK(self):
    for i in range(1, 11):
      for (if_suffix, s_param) in SUFFIX_PARAMS:
        for (bridge, b_param) in BRIDGE_PARAMS:
          bw = self.WlanConfiguration(
              'wifi0', if_suffix, bridge, device.Radio(), band='2.4')
          bw.StartTransaction()
          bw.RadioEnabled = True
          bw.Enable = True
          bw.AutoChannelEnable = True
          bw.SSID = 'Test SSID 1'
          bw.BeaconType = 'WPAand11i'
          bw.IEEE11iEncryptionModes = 'AESEncryption'
          bw.PreSharedKeyList[str(i)].KeyPassphrase = 'test password'
          ap, buf = self.GatherOutput(bw)
          exp = [
              'env', 'WIFI_PSK=test password', binwifi.BINWIFI[0],
              'set', '-P', '-b', '2.4', '-e', 'WPA12_PSK_AES', s_param,
              b_param,
              '-c', 'auto', '-s', 'Test SSID 1', '-p', 'a/b/g/n', '-M',
          ]
          self.assertTrue(ap)
          self.assertEqual(buf.strip().splitlines(), [l for l in exp if l])

  def testPasswordTriggers(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0', device.Radio(), band='2.4')
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID 1'
    bw.BeaconType = 'WPAand11i'
    bw.IEEE11iEncryptionModes = 'AESEncryption'
    bw.PreSharedKeyList['1'].KeyPassphrase = 'testpassword'
    _, buf = self.GatherOutput(bw)

    # Test that setting the KeyPassphrase alone is enough to write the config
    bw.PreSharedKeyList['1'].KeyPassphrase = ''
    for i in reversed(range(1, 11)):
      bw.PreSharedKeyList[str(i)].KeyPassphrase = 'testpassword' + str(i)
      _, newbuf = self.GatherOutput(bw)
      self.assertNotEqual(newbuf, buf)
      buf = newbuf

  def testWEP(self):
    for (if_suffix, s_param) in SUFFIX_PARAMS:
      for (bridge, b_param) in BRIDGE_PARAMS:
        bw = self.WlanConfiguration(
            'wifi0', if_suffix, bridge, device.Radio(), band='2.4')
        bw.StartTransaction()
        bw.RadioEnabled = True
        bw.Enable = True
        bw.AutoChannelEnable = True
        bw.SSID = 'Test SSID'
        bw.BeaconType = 'Basic'
        bw.BasicEncryptionModes = 'WEPEncryption'
        ap, buf = self.GatherOutput(bw)
        exp = [
            binwifi.BINWIFI[0],
            'set', '-P', '-b', '2.4', '-e', 'WEP', s_param, b_param,
            '-c', 'auto', '-s', 'Test SSID', '-p', 'a/b/g/n', '-M',
        ]
        self.assertTrue(ap)
        self.assertEqual(buf.strip().splitlines(), [l for l in exp if l])

  def testSSID(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0', device.Radio(), band='5')
    bw.StartTransaction()
    bw.SSID = 'this is ok'
    self.loop.RunOnce(timeout=1)
    bw.SSID = '0123456789abcdef0123456789abcdef'  # should still be ok
    self.loop.RunOnce(timeout=1)
    self.assertRaises(ValueError, setattr, bw, 'SSID',
                      '0123456789abcdef0123456789abcdef0')
    self.loop.RunOnce(timeout=1)

  # pylint: disable=protected-access
  def testMakeBinWifiCommandSecurity(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0', device.Radio(), band='5')
    bw.StartTransaction()
    bw.SSID = 'this is ok'
    bw.PreSharedKeyList['1'].KeyPassphrase = 'test password'
    bw._MakeBinWifiCommand()

    bw.SSID = 'this is\nnot ok'
    self.assertRaises(ValueError, bw._MakeBinWifiCommand)

    bw.SSID = 'also not ok\0'
    self.assertRaises(ValueError, bw._MakeBinWifiCommand)

    bw.SSID = 'this is ok'
    bw.PreSharedKeyList['1'].KeyPassphrase = 'test\npassword'
    self.assertRaises(ValueError, bw._MakeBinWifiCommand)

    bw.SSID = 'this is ok'
    bw.PreSharedKeyList['1'].KeyPassphrase = 'test password\0'
    self.assertRaises(ValueError, bw._MakeBinWifiCommand)

    bw.PreSharedKeyList['1'].KeyPassphrase = 'test password'
    self.loop.RunOnce(timeout=1)

  def testConmanFilenames(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0', device.Radio(), band='5')
    self.assertEqual(bw.WifiCommandFileName(),
                     os.path.join(binwifi.CONMAN_DIR[0], 'command.5'))
    self.assertEqual(bw.APEnabledFileName(),
                     os.path.join(binwifi.CONMAN_DIR[0], 'access_point.5'))
    bw._if_suffix = '_portal'
    self.assertEqual(bw.WifiCommandFileName(),
                     os.path.join(binwifi.CONMAN_TMP_DIR[0],
                                  'command._portal.5'))

  def testAssociatedDevices(self):
    binwifi.STATIONS_DIR[0] = 'testdata/binwifi/stations'
    bw = self.WlanConfiguration('wifi0', '', 'br0', device.Radio())
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
    bw = self.WlanConfiguration('wifi0', '', 'br0', device.Radio())
    self.assertEqual(bw.OperatingFrequencyBand, '5GHz')
    bw.OperatingFrequencyBand = '2.4GHz'
    self.assertEqual(bw.OperatingFrequencyBand, '2.4GHz')
    bw.OperatingFrequencyBand = ''
    self.assertEqual(bw.OperatingFrequencyBand, '5GHz')
    self.assertRaises(ValueError, setattr, bw,
                      'OperatingFrequencyBand', '60GHz')
    self.loop.RunOnce(timeout=1)

  def testOperatingFrequencyBand(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0', device.Radio())
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.OperatingFrequencyBand = '5GHz'
    bw.SSID = 'Test SSID'
    bw.BeaconType = 'Basic'
    bw.BasicEncryptionModes = 'None'
    _, buf = self.GatherOutput(bw)
    self.assertTrue('-b 5' in ' '.join(buf.splitlines()))

    bw.OperatingFrequencyBand = '2.4GHz'
    _, buf = self.GatherOutput(bw)
    self.assertTrue('-b 2.4' in ' '.join(buf.splitlines()))

  def testBeaconType(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0', device.Radio(), band='5')
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
    _, buf = self.GatherOutput(bw)
    self.assertTrue('WPA2_PSK_AES' in ' '.join(buf.splitlines()))
    bw.BeaconType = 'WPA'
    _, buf = self.GatherOutput(bw)
    self.assertTrue('WPA_PSK_AES' in ' '.join(buf.splitlines()))
    bw.BeaconType = 'WPAand11i'
    _, buf = self.GatherOutput(bw)
    self.assertTrue('WPA12_PSK_AES' in ' '.join(buf.splitlines()))

  def testStandard(self):
    bw = self.WlanConfiguration(
        'wifi0', '', 'br0', device.Radio(), band='5', width_5g=80)
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
    _, buf = self.GatherOutput(bw)
    self.assertTrue('-p a/b/g/n/ac' in ' '.join(buf.splitlines()))
    self.assertTrue('-M' in shlex.split(buf))  # always enabled for n/ac modes
    self.assertTrue('-G' not in shlex.split(buf))

    bw.GuardInterval = '400nsec'
    _, buf = self.GatherOutput(bw)
    self.assertTrue('-G' in shlex.split(buf))
    self.assertTrue('-Y' not in shlex.split(buf))
    self.assertTrue('-X' not in shlex.split(buf))
    self.assertTrue('-XX' not in shlex.split(buf))

    bw.RekeyingInterval = 0
    _, buf = self.GatherOutput(bw)
    self.assertTrue('-Y' in shlex.split(buf))
    self.assertTrue('-X' not in shlex.split(buf))
    self.assertTrue('-XX' not in shlex.split(buf))

    bw.RekeyingInterval = 1
    _, buf = self.GatherOutput(bw)
    self.assertTrue('-Y' not in shlex.split(buf))
    self.assertTrue('-X' in shlex.split(buf))
    self.assertTrue('-XX' not in shlex.split(buf))

    bw.RekeyingInterval = 10
    _, buf = self.GatherOutput(bw)
    self.assertTrue('-Y' not in shlex.split(buf))
    self.assertTrue('-X ' not in shlex.split(buf))
    self.assertTrue('-XX' in shlex.split(buf))

    bw.Standard = 'n'
    _, buf = self.GatherOutput(bw)
    self.assertTrue('-p a/b/g/n' in ' '.join(buf.splitlines()))
    self.assertTrue('-M' in shlex.split(buf))  # always enabled for n/ac modes

    bw.Standard = 'g'
    _, buf = self.GatherOutput(bw)
    self.assertTrue('-p a/b/g' in ' '.join(buf.splitlines()))
    self.assertTrue('-M' not in shlex.split(buf))  # not auto-enabled

    bw.WMMEnable = True
    _, buf = self.GatherOutput(bw)
    self.assertTrue('-M' in shlex.split(buf))

    bw.Standard = 'b'
    _, buf = self.GatherOutput(bw)
    # We set 'a/b' and expect OperatingFrequencyBand to determine the band.
    self.assertTrue('-p a/b' in ' '.join(buf.splitlines()))

    bw.Standard = 'a'
    _, buf = self.GatherOutput(bw)
    # No output, because 'a' is the same as the previous 'b', so wifi doesn't
    # need to restart.
    self.assertEqual(buf, '')

    bw.Standard = 'g'
    _, buf = self.GatherOutput(bw)
    bw.Standard = 'a'
    _, buf = self.GatherOutput(bw)
    # Same output as 'b'
    self.assertTrue('-p a/b' in ' '.join(buf.splitlines()))

  def testClientIsolation(self):
    bw = self.WlanConfiguration(
        'wifi0', '_portal', 'br1', band='5', width_5g=80)
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.SSID = 'Test SSID 1'
    _, buf = self.GatherOutput(bw)
    self.assertFalse('-C' in ' '.join(buf.splitlines()))

    bw.X_CATAWAMPUS_ORG_ClientIsolation = True
    _, buf = self.GatherOutput(bw)
    self.assertTrue('-C' in ' '.join(buf.splitlines()))

  def testWidth(self):
    bw = self.WlanConfiguration(
        'wifi0', '', 'br0', device.Radio(), band='5', width_5g=80)
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID 1'
    _, buf = self.GatherOutput(bw)
    self.assertTrue('-w 80' in ' '.join(buf.splitlines()))

    bw = self.WlanConfiguration(
        'wifi0', '', 'br0', device.Radio(), band='5', width_2_4g=40)
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID 1'
    _, buf = self.GatherOutput(bw)
    self.assertFalse('-w 40' in ' '.join(buf.splitlines()))

    bw = self.WlanConfiguration(
        'wifi0', '', 'br0', device.Radio(), band='2.4', width_2_4g=40)
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID 1'
    _, buf = self.GatherOutput(bw)
    self.assertTrue('-w 40' in ' '.join(buf.splitlines()))

    bw = self.WlanConfiguration(
        'wifi0', '', 'br0', device.Radio(), band='2.4', width_5g=80)
    bw.StartTransaction()
    bw.RadioEnabled = True
    bw.Enable = True
    bw.AutoChannelEnable = True
    bw.SSID = 'Test SSID 1'
    _, buf = self.GatherOutput(bw)
    self.assertFalse('-w 80' in ' '.join(buf.splitlines()))

  def testAutoDisableRecommended(self):
    bw = self.WlanConfiguration('wifi0', '', 'br0', device.Radio(), band='5')
    self.assertFalse(bw.X_CATAWAMPUS_ORG_AutoDisableRecommended)
    open(self.tmpdir + '/wifi0.disabled', 'w').write('')
    self.assertTrue(bw.X_CATAWAMPUS_ORG_AutoDisableRecommended)
    open(self.tmpdir + '/wifi0.disabled', 'w').write('f8:8f:ca:00:00:01')
    self.assertTrue(bw.X_CATAWAMPUS_ORG_AutoDisableRecommended)


if __name__ == '__main__':
  unittest.main()

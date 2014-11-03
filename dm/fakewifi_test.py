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
# pylint:disable=invalid-name

"""Unit tests for brcmwifi.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
from tr.wvtest import unittest
import fakewifi


class BrcmWifiTest(unittest.TestCase):
  def testValidateExports(self):
    wifi = fakewifi.FakeWifiWlanConfiguration()
    wifi.ValidateExports()

  def testChannel(self):
    wifi = fakewifi.FakeWifiWlanConfiguration()
    self.assertEqual(wifi.Channel, 1)
    wifi.Channel = 2
    self.assertEqual(wifi.Channel, 2)
    self.assertRaises(ValueError, setattr, wifi, 'Channel', 166)
    self.assertRaises(ValueError, setattr, wifi, 'Channel', 14)
    self.assertRaises(ValueError, setattr, wifi, 'Channel', 0)
    self.assertRaises(ValueError, setattr, wifi, 'Channel', 20)

  def testSSID(self):
    wifi = fakewifi.FakeWifiWlanConfiguration()
    wifi.SSID = r'myssid'
    self.assertEqual(wifi.SSID, 'myssid')
    wifi.SSID = r'my ssid'
    self.assertEqual(wifi.SSID, 'my ssid')
    self.assertRaises(ValueError, wifi.SetSSID,
                      r'myssidiswaaaaaaaaaaaaaaaaaaaaaaaaaaytoolongtovalidate')

  def testBSSID(self):
    wifi = fakewifi.FakeWifiWlanConfiguration()
    wifi.BSSID = '00:00:0f:00:00:12'
    self.assertEqual(wifi.BSSID, '00:00:0f:00:00:12')

  def testFixedParameters(self):
    wifi = fakewifi.FakeWifiWlanConfiguration()
    self.assertFalse(wifi.AutoRateFallBackEnabled)
    self.assertEqual(wifi.BasicDataTransmitRates,
                     '1,2,5.5,6,9,11,12,18,24,36,48,54')
    self.assertEqual(wifi.DeviceOperationMode, 'InfrastructureAccessPoint')
    self.assertEqual(wifi.Name, 'fakewifi0')
    self.assertEqual(wifi.OperationalDataTransmitRates,
                     '1,2,5.5,6,9,11,12,18,24,36,48,54')
    self.assertEqual(wifi.PossibleChannels,
                     '1-11,36,40,44,48,52,56,60,64,100,104,108,112,116,120,124,'
                     '128,132,136,140,149,153,157,161,165')
    self.assertEqual(wifi.RegulatoryDomain, 'US')
    self.assertEqual(wifi.Standard, 'n')
    self.assertEqual(wifi.TotalBytesReceived, 2000000)
    self.assertEqual(wifi.TotalBytesSent, 1000000)
    self.assertEqual(wifi.TotalPacketsReceived, 2000)
    self.assertEqual(wifi.TotalPacketsSent, 1000)
    self.assertEqual(wifi.TransmitPowerSupported, '1-100')
    self.assertFalse(wifi.UAPSDSupported)
    self.assertEqual(wifi.WEPEncryptionLevel, 'Disabled,40-bit,104-bit')
    self.assertFalse(wifi.WMMSupported)

  def testTransmitPower(self):
    wifi = fakewifi.FakeWifiWlanConfiguration()
    self.assertEqual(wifi.TransmitPower, 100)
    self.assertRaises(ValueError, wifi.SetTransmitPower, 101)
    self.assertRaises(ValueError, wifi.SetTransmitPower, 'foo')

  def testSSIDAdvertisementEnabled(self):
    wifi = fakewifi.FakeWifiWlanConfiguration()
    self.assertTrue(wifi.SSIDAdvertisementEnabled)
    wifi.SSIDAdvertisementEnabled = False
    self.assertFalse(wifi.SSIDAdvertisementEnabled)
    self.assertRaises(ValueError, setattr, wifi,
                      'SSIDAdvertisementEnabled', 'Invalid')

  def testRadioEnabled(self):
    wifi = fakewifi.FakeWifiWlanConfiguration()
    self.assertFalse(wifi.RadioEnabled)
    wifi.RadioEnabled = True
    self.assertTrue(wifi.RadioEnabled)
    self.assertRaises(ValueError, setattr, wifi, 'RadioEnabled', 'Invalid')

  def testAutoRateFallBackEnabled(self):
    wifi = fakewifi.FakeWifiWlanConfiguration()
    self.assertFalse(wifi.AutoRateFallBackEnabled)
    wifi.AutoRateFallBackEnabled = True
    self.assertTrue(wifi.AutoRateFallBackEnabled)
    self.assertRaises(ValueError, setattr, wifi,
                      'AutoRateFallBackEnabled', 'Invalid')

  def testEnable(self):
    wifi = fakewifi.FakeWifiWlanConfiguration()
    self.assertFalse(wifi.Enable)
    wifi.Enable = True
    self.assertTrue(wifi.Enable)
    self.assertRaises(ValueError, setattr, wifi, 'Enable', 'Invalid')

  def testInvalidEncryptionModes(self):
    wifi = fakewifi.FakeWifiWlanConfiguration()
    self.assertRaises(ValueError, setattr, wifi,
                      'BasicEncryptionModes', 'invalid')
    self.assertRaises(ValueError, setattr, wifi,
                      'IEEE11iEncryptionModes', 'invalid')
    self.assertRaises(ValueError, setattr, wifi,
                      'WPAEncryptionModes', 'invalid')

  def testBeaconType(self):
    wifi = fakewifi.FakeWifiWlanConfiguration()
    wifi.BeaconType = 'None'
    self.assertEqual(wifi.BeaconType, 'None')
    wifi.BeaconType = 'Basic'
    self.assertEqual(wifi.BeaconType, 'Basic')
    wifi.BeaconType = 'WPA'
    self.assertEqual(wifi.BeaconType, 'WPA')
    wifi.BeaconType = '11i'
    self.assertEqual(wifi.BeaconType, '11i')
    wifi.BeaconType = 'BasicandWPA'
    self.assertEqual(wifi.BeaconType, 'BasicandWPA')
    wifi.BeaconType = 'Basicand11i'
    self.assertEqual(wifi.BeaconType, 'Basicand11i')
    wifi.BeaconType = 'WPAand11i'
    self.assertEqual(wifi.BeaconType, 'WPAand11i')
    wifi.BeaconType = 'BasicandWPAand11i'
    self.assertEqual(wifi.BeaconType, 'BasicandWPAand11i')
    self.assertRaises(ValueError, setattr, wifi, 'BeaconType', 'FooFi')

  def testAuthenticationMode(self):
    wifi = fakewifi.FakeWifiWlanConfiguration()
    self.assertRaises(ValueError, setattr, wifi,
                      'BasicAuthenticationMode', 'Invalid')
    wifi.BasicAuthenticationMode = 'None'
    self.assertEqual(wifi.BasicAuthenticationMode, 'None')
    wifi.BasicAuthenticationMode = 'SharedAuthentication'
    self.assertEqual(wifi.BasicAuthenticationMode, 'SharedAuthentication')
    wifi.BasicEncryptionModes = 'WEPEncryption'
    self.assertEqual(wifi.BasicEncryptionModes, 'WEPEncryption')

    wifi.IEEE11iAuthenticationMode = 'PSKAuthentication'
    self.assertEqual(wifi.IEEE11iAuthenticationMode, 'PSKAuthentication')
    wifi.IEEE11iEncryptionModes = 'AESEncryption'
    self.assertEqual(wifi.IEEE11iEncryptionModes, 'AESEncryption')
    self.assertRaises(ValueError, setattr, wifi,
                      'IEEE11iAuthenticationMode', 'Invalid')

    wifi.WPAAuthenticationMode = 'PSKAuthentication'
    self.assertEqual(wifi.WPAAuthenticationMode, 'PSKAuthentication')
    wifi.WPAEncryptionModes = 'TKIPEncryption'
    self.assertEqual(wifi.WPAEncryptionModes, 'TKIPEncryption')
    self.assertRaises(ValueError, setattr, wifi,
                      'WPAAuthenticationMode', 'Invalid')
    self.assertRaises(ValueError, setattr, wifi,
                      'WPAEncryptionModes', 'Invalid')

  def testStats(self):
    wifi = fakewifi.FakeWifiWlanConfiguration()
    self.assertEqual(wifi.Stats.ErrorsSent, 1)
    self.assertEqual(wifi.Stats.ErrorsReceived, 2)
    self.assertEqual(wifi.Stats.UnicastPacketsSent, 1000000)
    self.assertEqual(wifi.Stats.UnicastPacketsReceived, 2000000)
    self.assertEqual(wifi.Stats.DiscardPacketsSent, 3)
    self.assertEqual(wifi.Stats.DiscardPacketsReceived, 4)
    self.assertEqual(wifi.Stats.MulticastPacketsSent, 1000)
    self.assertEqual(wifi.Stats.MulticastPacketsReceived, 2000)
    self.assertEqual(wifi.Stats.BroadcastPacketsSent, 10000)
    self.assertEqual(wifi.Stats.BroadcastPacketsReceived, 20000)
    self.assertEqual(wifi.Stats.UnknownProtoPacketsReceived, 5)

  def testAssociatedDevices(self):
    wifi = fakewifi.FakeWifiWlanConfiguration()
    self.assertEqual(wifi.TotalAssociations, 2)
    assoc = wifi.AssociatedDeviceList[1]
    self.assertEqual(assoc.AssociatedDeviceMACAddress, '00:01:02:03:04:05')
    assoc = wifi.AssociatedDeviceList[2]
    self.assertEqual(assoc.AssociatedDeviceMACAddress, '00:01:02:03:04:06')


if __name__ == '__main__':
  unittest.main()

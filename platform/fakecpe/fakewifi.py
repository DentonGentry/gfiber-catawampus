#!/usr/bin/python
# Copyright 2013 Google Inc. All Rights Reserved.
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

# TR-069 has mandatory attribute names that don't comply with policy
# pylint: disable-msg=C6409

"""Implementation of tr-98 WLAN objects for FakeCPE.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import dm.wifi
import tr.core
import tr.cwmpbool
import tr.session
import tr.tr098_v1_4
import tr.types

BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice
BASE98WIFI = BASE98IGD.LANDevice.WLANConfiguration
BASICAUTHMODES = frozenset(['None', 'SharedAuthentication'])
BASICENCRYPTIONS = frozenset(['None', 'WEPEncryption'])
BEACONS = frozenset(['None', 'Basic', 'WPA', '11i', 'BasicandWPA',
                     'Basicand11i', 'WPAand11i', 'BasicandWPAand11i'])
POSSIBLECHANNELS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 36, 40, 44, 48, 52, 56,
                    60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136,
                    140, 149, 153, 157, 161, 165]
WPAAUTHMODES = frozenset(['PSKAuthentication'])
WPAENCRYPTIONMODES = frozenset(
    ['WEPEncryption', 'TKIPEncryption', 'WEPandTKIPEncryption',
     'AESEncryption', 'WEPandAESEncryption', 'TKIPandAESEncryption',
     'WEPandTKIPandAESEncryption'])


class FakeWifiStats(BASE98WIFI.Stats):
  """tr98 InternetGatewayDevice.LANDevice.WLANConfiguration.Stats."""

  ErrorsSent = tr.types.ReadOnlyUnsigned(1)
  ErrorsReceived = tr.types.ReadOnlyUnsigned(2)
  UnicastPacketsSent = tr.types.ReadOnlyUnsigned(1000000)
  UnicastPacketsReceived = tr.types.ReadOnlyUnsigned(2000000)
  DiscardPacketsSent = tr.types.ReadOnlyUnsigned(3)
  DiscardPacketsReceived = tr.types.ReadOnlyUnsigned(4)
  MulticastPacketsSent = tr.types.ReadOnlyUnsigned(1000)
  MulticastPacketsReceived = tr.types.ReadOnlyUnsigned(2000)
  BroadcastPacketsSent = tr.types.ReadOnlyUnsigned(10000)
  BroadcastPacketsReceived = tr.types.ReadOnlyUnsigned(20000)
  UnknownProtoPacketsReceived = tr.types.ReadOnlyUnsigned(5)


class FakeWifiAssociatedDevice(BASE98WIFI.AssociatedDevice):
  AssociatedDeviceMACAddress = tr.types.ReadOnlyString('00:11:22:33:44:55')
  AssociatedDeviceAuthenticationState = tr.types.ReadOnlyBool(True)

  def __init__(self, mac=None, ip=None):
    super(FakeWifiAssociatedDevice, self).__init__()
    self.Unexport('AssociatedDeviceIPAddress')
    self.Unexport('LastRequestedUnicastCipher')
    self.Unexport('LastRequestedMulticastCipher')
    self.Unexport('LastPMKId')
    self.Unexport('LastDataTransmitRate')
    if mac:
      type(self).AssociatedDeviceMACAddress.Set(self, mac)


class FakeWifiWlanConfiguration(BASE98WIFI):
  """An implementation of tr98 WLANConfiguration for FakeCPE."""
  BasicDataTransmitRates = tr.types.ReadOnlyString(
      '1,2,5.5,6,9,11,12,18,24,36,48,54')
  Name = tr.types.ReadOnlyString('fakewifi0')
  Standard = tr.types.ReadOnlyString('n')
  DeviceOperationMode = tr.types.ReadOnlyString('InfrastructureAccessPoint')
  OperationalDataTransmitRates = tr.types.ReadOnlyString(
      '1,2,5.5,6,9,11,12,18,24,36,48,54')
  PossibleChannels = tr.types.ReadOnlyString(
      dm.wifi.ContiguousRanges(POSSIBLECHANNELS))
  TotalBytesSent = tr.types.ReadOnlyUnsigned(1000000)
  TotalPacketsSent = tr.types.ReadOnlyUnsigned(1000)
  TotalPacketsReceived = tr.types.ReadOnlyUnsigned(2000)
  TotalBytesReceived = tr.types.ReadOnlyUnsigned(2000000)
  TransmitPowerSupported = tr.types.ReadOnlyString('1-100')
  UAPSDSupported = tr.types.ReadOnlyBool(False)
  WEPEncryptionLevel = tr.types.ReadOnlyString('Disabled,40-bit,104-bit')
  WMMSupported = tr.types.ReadOnlyBool(False)

  def __init__(self):
    super(FakeWifiWlanConfiguration, self).__init__()

    # Unimplemented, but not yet evaluated
    self.Unexport('Alias')
    self.Unexport('BeaconAdvertisementEnabled')
    self.Unexport('ChannelsInUse')
    self.Unexport('MaxBitRate')
    self.Unexport('PossibleDataTransmitRates')
    self.Unexport('TotalIntegrityFailures')
    self.Unexport('TotalPSKFailures')

    # No RADIUS support, could be added later.
    self.Unexport('AuthenticationServiceMode')

    # Local settings, currently unimplemented. Will require more
    # coordination with the underlying platform support.
    self.Unexport('InsecureOOBAccessEnabled')

    # MAC Access controls, currently unimplemented but could be supported.
    self.Unexport('MACAddressControlEnabled')

    # Wifi Protected Setup, currently unimplemented and not recommended.
    self.Unexport(objects='WPS')

    # Wifi MultiMedia, currently unimplemented but could be supported.
    # "wl wme_*" commands
    self.Unexport(lists='APWMMParameter')
    self.Unexport(lists='STAWMMParameter')
    self.Unexport('UAPSDEnable')
    self.Unexport('WMMEnable')

    # WDS, currently unimplemented but could be supported at some point.
    self.Unexport('PeerBSSID')
    self.Unexport('DistanceFromRoot')

    self.auto_channel_enable = True
    self.auto_rate_fallback_enabled = False
    self.basic_authentication_mode = 'None'
    self.basic_encryption_mode = 'None'
    self.beacon_type = 'None'
    self.BSSID = '00:1a:11:00:00:01'
    self.channel = 1
    self.enable = False
    self.ieee11i_authentication_mode = 'PSKAuthentication'
    self.ieee11i_encryption_modes = 'AESEncryption'
    self.LocationDescription = ''
    self.radio_enabled = False
    self.RegulatoryDomain = 'US'
    self.ssid = ''
    self.ssid_advertisement_enabled = True
    self.transmit_power = 100
    self.wepkeyindex = 0
    self.wpa_authentication_mode = 'PSKAuthentication'
    self.wpa_encryption_modes = 'AESEncryption'

    self.PreSharedKeyList = {}
    for i in range(1, 11):
      self.PreSharedKeyList[i] = dm.wifi.PreSharedKey98()

    self.WEPKeyList = {}
    for i in range(1, 5):
      self.WEPKeyList[i] = dm.wifi.WEPKey98()

    self.AssociatedDeviceList = {
        1: FakeWifiAssociatedDevice(mac='00:01:02:03:04:05'),
        2: FakeWifiAssociatedDevice(mac='00:01:02:03:04:06'),
    }
    self.Stats = FakeWifiStats()

  @property
  def TotalAssociations(self):
    return len(self.AssociatedDeviceList)

  def GetBasicAuthenticationMode(self):
    return self.basic_authentication_mode

  def SetBasicAuthenticationMode(self, value):
    if not value in BASICAUTHMODES:
      raise ValueError('Unsupported BasicAuthenticationMode %s' % value)
    self.basic_authentication_mode = value

  BasicAuthenticationMode = property(
      GetBasicAuthenticationMode, SetBasicAuthenticationMode, None,
      'WLANConfiguration.BasicAuthenticationMode')

  def GetAutoRateFallBackEnabled(self):
    return self.auto_rate_fallback_enabled

  def SetAutoRateFallBackEnabled(self, value):
    self.auto_rate_fallback_enabled = tr.cwmpbool.parse(value)

  AutoRateFallBackEnabled = property(
      GetAutoRateFallBackEnabled, SetAutoRateFallBackEnabled, None,
      'WLANConfiguration.AutoRateFallBackEnabled')

  def GetBasicEncryptionModes(self):
    return self.basic_encryption_mode

  def SetBasicEncryptionModes(self, value):
    if value not in BASICENCRYPTIONS:
      raise ValueError('Unsupported BasicEncryptionMode: %s' % value)
    self.basic_encryption_mode = value

  BasicEncryptionModes = property(GetBasicEncryptionModes,
                                  SetBasicEncryptionModes, None,
                                  'WLANConfiguration.BasicEncryptionModes')

  def GetBeaconType(self):
    return self.beacon_type

  def SetBeaconType(self, value):
    if value not in BEACONS:
      raise ValueError('Unsupported BeaconType: %s' % value)
    self.beacon_type = value

  BeaconType = property(GetBeaconType, SetBeaconType, None,
                        'WLANConfiguration.BeaconType')

  def GetChannel(self):
    return self.channel

  def SetChannel(self, value):
    channel = int(value)
    if channel not in POSSIBLECHANNELS:
      raise ValueError('Channel %d is not in PossibleChannels' % channel)
    self.channel = channel
    self.auto_channel_enable = False

  Channel = property(GetChannel, SetChannel, None, 'WLANConfiguration.Channel')

  def GetEnable(self):
    return self.enable

  def SetEnable(self, value):
    self.enable = tr.cwmpbool.parse(value)

  Enable = property(GetEnable, SetEnable, None, 'WLANConfiguration.Enable')

  def GetIEEE11iAuthenticationMode(self):
    return self.ieee11i_authentication_mode

  def SetIEEE11iAuthenticationMode(self, value):
    if not value in WPAAUTHMODES:
      raise ValueError('Unsupported IEEE11iAuthenticationMode %s' % value)
    self.ieee11i_authentication_mode = value

  IEEE11iAuthenticationMode = property(
      GetIEEE11iAuthenticationMode, SetIEEE11iAuthenticationMode,
      None, 'WLANConfiguration.IEEE11iAuthenticationMode')

  def GetIEEE11iEncryptionModes(self):
    return self.ieee11i_encryption_modes

  def SetIEEE11iEncryptionModes(self, value):
    if not value in WPAENCRYPTIONMODES:
      raise ValueError('Unsupported IEEE11iEncryptionModes %s' % value)
    self.ieee11i_encryption_modes = value

  IEEE11iEncryptionModes = property(GetIEEE11iEncryptionModes,
                                    SetIEEE11iEncryptionModes,
                                    None,
                                    'WLANConfiguration.IEEE11iEncryptionModes')

  def GetKeyPassphrase(self):
    psk = self.PreSharedKeyList[1]
    return psk.KeyPassphrase

  def SetKeyPassphrase(self, value):
    psk = self.PreSharedKeyList[1]
    psk.KeyPassphrase = value
    # TODO(dgentry) need to set WEPKeys, but this is fraught with peril.
    # If KeyPassphrase is not exactly 5 or 13 bytes it must be padded.
    # Apple uses different padding than Windows (and others).
    # http://support.apple.com/kb/HT1344

  KeyPassphrase = property(GetKeyPassphrase, SetKeyPassphrase, None,
                           'WLANConfiguration.KeyPassphrase')

  def GetRadioEnabled(self):
    return self.radio_enabled

  def SetRadioEnabled(self, value):
    self.radio_enabled = tr.cwmpbool.parse(value)

  RadioEnabled = property(GetRadioEnabled, SetRadioEnabled, None,
                          'WLANConfiguration.RadioEnabled')

  def GetAutoChannelEnable(self):
    return self.auto_channel_enable

  def SetAutoChannelEnable(self, value):
    self.auto_channel_enable = tr.cwmpbool.parse(value)

  AutoChannelEnable = property(GetAutoChannelEnable, SetAutoChannelEnable,
                               None, 'WLANConfiguration.AutoChannelEnable')

  def GetSSID(self):
    return self.ssid

  def SetSSID(self, value):
    if len(value) > 32:
      raise ValueError('SSID must be <= 32 characters in length')
    self.ssid = value

  SSID = property(GetSSID, SetSSID, None, 'WLANConfiguration.SSID')

  def GetSSIDAdvertisementEnabled(self):
    return self.ssid_advertisement_enabled

  def SetSSIDAdvertisementEnabled(self, value):
    self.ssid_advertisement_enabled = tr.cwmpbool.parse(value)

  SSIDAdvertisementEnabled = property(
      GetSSIDAdvertisementEnabled, SetSSIDAdvertisementEnabled, None,
      'WLANConfiguration.SSIDAdvertisementEnabled')

  def GetBssStatus(self):
    return 'Up' if self.enable else 'Disabled'

  Status = property(GetBssStatus, None, None, 'WLANConfiguration.Status')

  def GetTransmitPower(self):
    return self.transmit_power

  def SetTransmitPower(self, value):
    v = int(value)
    if v < 1 or v > 100:
      raise ValueError('TransmitPower must be 1-100')
    self.transmit_power = v

  TransmitPower = property(GetTransmitPower, SetTransmitPower, None,
                           'WLANConfiguration.TransmitPower')

  def GetWEPKeyIndex(self):
    return self.wepkeyindex

  def SetWEPKeyIndex(self, value):
    self.wepkeyindex = int(value)

  WEPKeyIndex = property(GetWEPKeyIndex, SetWEPKeyIndex, None,
                         'WLANConfiguration.WEPKeyIndex')

  def GetWPAAuthenticationMode(self):
    return self.wpa_authentication_mode

  def SetWPAAuthenticationMode(self, value):
    if not value in WPAAUTHMODES:
      raise ValueError('Unsupported WPAAuthenticationMode %s' % value)
    self.wpa_authentication_mode = value

  WPAAuthenticationMode = property(
      GetWPAAuthenticationMode, SetWPAAuthenticationMode,
      None, 'WLANConfiguration.WPAAuthenticationMode')

  def GetWPAEncryptionModes(self):
    return self.wpa_encryption_modes

  def SetWPAEncryptionModes(self, value):
    if not value in WPAENCRYPTIONMODES:
      raise ValueError('Unsupported WPAEncryptionModes %s' % value)
    self.wpa_encryption_modes = value

  WPAEncryptionModes = property(GetWPAEncryptionModes, SetWPAEncryptionModes,
                                None, 'WLANConfiguration.WPAEncryptionModes')

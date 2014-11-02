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
# pylint:disable=invalid-name

"""Implementation of tr-98 WLAN objects for FakeCPE.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import dm.wifi
import tr.core
import tr.cwmpbool
import tr.session
import tr.tr098_v1_4
import tr.cwmptypes

BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice
BASE98WIFI = BASE98IGD.LANDevice.WLANConfiguration
POSSIBLECHANNELS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 36, 40, 44, 48, 52, 56,
                    60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136,
                    140, 149, 153, 157, 161, 165]


class FakeWifiStats(BASE98WIFI.Stats):
  """tr98 InternetGatewayDevice.LANDevice.WLANConfiguration.Stats."""

  ErrorsSent = tr.cwmptypes.ReadOnlyUnsigned(1)
  ErrorsReceived = tr.cwmptypes.ReadOnlyUnsigned(2)
  UnicastPacketsSent = tr.cwmptypes.ReadOnlyUnsigned(1000000)
  UnicastPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(2000000)
  DiscardPacketsSent = tr.cwmptypes.ReadOnlyUnsigned(3)
  DiscardPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(4)
  MulticastPacketsSent = tr.cwmptypes.ReadOnlyUnsigned(1000)
  MulticastPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(2000)
  BroadcastPacketsSent = tr.cwmptypes.ReadOnlyUnsigned(10000)
  BroadcastPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(20000)
  UnknownProtoPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(5)


class FakeWifiAssociatedDevice(BASE98WIFI.AssociatedDevice):
  AssociatedDeviceMACAddress = tr.cwmptypes.ReadOnlyMacAddr('00:11:22:33:44:55')
  AssociatedDeviceAuthenticationState = tr.cwmptypes.ReadOnlyBool(True)

  def __init__(self, mac=None, ip=None):
    super(FakeWifiAssociatedDevice, self).__init__()
    self.Unexport(['AssociatedDeviceIPAddress', 'LastRequestedUnicastCipher',
                   'LastRequestedMulticastCipher', 'LastPMKId',
                   'LastDataTransmitRate'])
    if mac:
      type(self).AssociatedDeviceMACAddress.Set(self, mac)


class FakeWifiWlanConfiguration(BASE98WIFI):
  """An implementation of tr98 WLANConfiguration for FakeCPE."""

  AutoChannelEnable = tr.cwmptypes.Bool(True)
  AutoRateFallBackEnabled = tr.cwmptypes.Bool(False)
  BasicAuthenticationMode = tr.cwmptypes.Enum(['None', 'SharedAuthentication'])
  BasicDataTransmitRates = tr.cwmptypes.ReadOnlyString(
      '1,2,5.5,6,9,11,12,18,24,36,48,54')
  BasicEncryptionModes = tr.cwmptypes.Enum(['None', 'WEPEncryption'])
  BeaconType = tr.cwmptypes.Enum(
      ['None', 'Basic', 'WPA', '11i', 'BasicandWPA', 'Basicand11i',
       'WPAand11i', 'BasicandWPAand11i'])
  BSSID = tr.cwmptypes.String('00:1a:11:00:00:01')
  DeviceOperationMode = tr.cwmptypes.ReadOnlyString('InfrastructureAccessPoint')
  Enable = tr.cwmptypes.Bool(False)
  IEEE11iAuthenticationMode = tr.cwmptypes.Enum(['PSKAuthentication'])
  IEEE11iEncryptionModes = tr.cwmptypes.Enum(
      ['WEPEncryption', 'TKIPEncryption', 'WEPandTKIPEncryption',
       'AESEncryption', 'WEPandAESEncryption', 'TKIPandAESEncryption',
       'WEPandTKIPandAESEncryption'])
  Name = tr.cwmptypes.ReadOnlyString('fakewifi0')
  OperationalDataTransmitRates = tr.cwmptypes.ReadOnlyString(
      '1,2,5.5,6,9,11,12,18,24,36,48,54')
  PossibleChannels = tr.cwmptypes.ReadOnlyString(
      dm.wifi.ContiguousRanges(POSSIBLECHANNELS))
  RadioEnabled = tr.cwmptypes.Bool(False)
  SSIDAdvertisementEnabled = tr.cwmptypes.Bool(True)
  Standard = tr.cwmptypes.ReadOnlyString('n')
  TotalBytesSent = tr.cwmptypes.ReadOnlyUnsigned(1000000)
  TotalPacketsSent = tr.cwmptypes.ReadOnlyUnsigned(1000)
  TotalPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(2000)
  TotalBytesReceived = tr.cwmptypes.ReadOnlyUnsigned(2000000)
  TransmitPowerSupported = tr.cwmptypes.ReadOnlyString('1-100')
  UAPSDSupported = tr.cwmptypes.ReadOnlyBool(False)
  WEPEncryptionLevel = tr.cwmptypes.ReadOnlyString('Disabled,40-bit,104-bit')
  WEPKeyIndex = tr.cwmptypes.Unsigned(0)
  WMMSupported = tr.cwmptypes.ReadOnlyBool(False)
  WPAAuthenticationMode = tr.cwmptypes.Enum(['PSKAuthentication'])
  WPAEncryptionModes = tr.cwmptypes.Enum(
      ['WEPEncryption', 'TKIPEncryption', 'WEPandTKIPEncryption',
       'AESEncryption', 'WEPandAESEncryption', 'TKIPandAESEncryption',
       'WEPandTKIPandAESEncryption'])

  def __init__(self):
    super(FakeWifiWlanConfiguration, self).__init__()

    # Unimplemented, but not yet evaluated
    self.Unexport(['Alias', 'BeaconAdvertisementEnabled', 'ChannelsInUse',
                   'MaxBitRate', 'PossibleDataTransmitRates',
                   'TotalIntegrityFailures', 'TotalPSKFailures'])

    # No RADIUS support, could be added later.
    self.Unexport(['AuthenticationServiceMode'])

    # Local settings, currently unimplemented. Will require more
    # coordination with the underlying platform support.
    self.Unexport(['InsecureOOBAccessEnabled'])

    # MAC Access controls, currently unimplemented but could be supported.
    self.Unexport(['MACAddressControlEnabled'])

    # Wifi Protected Setup, currently unimplemented and not recommended.
    self.Unexport(objects=['WPS'])

    # Wifi MultiMedia, currently unimplemented but could be supported.
    # "wl wme_*" commands
    self.Unexport(lists=['APWMMParameter', 'STAWMMParameter'])
    self.Unexport(['UAPSDEnable', 'WMMEnable'])

    # WDS, currently unimplemented but could be supported at some point.
    self.Unexport(['PeerBSSID', 'DistanceFromRoot'])

    self.channel = 1
    self.LocationDescription = ''
    self.RegulatoryDomain = 'US'
    self.ssid = ''
    self.transmit_power = 100

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

  def GetChannel(self):
    return self.channel

  def SetChannel(self, value):
    channel = int(value)
    if channel not in POSSIBLECHANNELS:
      raise ValueError('Channel %d is not in PossibleChannels' % channel)
    self.channel = channel
    self.AutoChannelEnable = False

  Channel = property(GetChannel, SetChannel, None, 'WLANConfiguration.Channel')

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

  def GetSSID(self):
    return self.ssid

  def SetSSID(self, value):
    if len(value) > 32:
      raise ValueError('SSID must be <= 32 characters in length')
    self.ssid = value

  SSID = property(GetSSID, SetSSID, None, 'WLANConfiguration.SSID')

  def GetBssStatus(self):
    return 'Up' if self.Enable else 'Disabled'

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

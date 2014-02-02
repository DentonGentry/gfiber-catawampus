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

# TR-069 has mandatory attribute names that don't comply with policy
# pylint: disable-msg=C6409

"""Implementation of tr-98 WLAN objects for /bin/wifi.

The platform code is expected to set the BSSID (which is really a MAC address).
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import subprocess
import traceback
import tr.mainloop
import tr.tr098_v1_6
import tr.x_catawampus_tr098_1_0
import netdev
import wifi

BASE98IGD = tr.tr098_v1_6.InternetGatewayDevice_v1_12.InternetGatewayDevice
BASE98WIFI = BASE98IGD.LANDevice.WLANConfiguration
CATA98 = tr.x_catawampus_tr098_1_0.X_CATAWAMPUS_ORG_InternetGatewayDevice_v1_0
CATA98WIFI = CATA98.InternetGatewayDevice.LANDevice.WLANConfiguration


# Unit tests can override these.
BINWIFI = ['wifi']


class WlanConfiguration(CATA98WIFI):
  """An implementation of tr98 WLANConfiguration for /bin/wifi."""
  encryption_modes = ['X_CATAWAMPUS-ORG_None', 'None', 'WEPEncryption',
                      'TKIPEncryption', 'WEPandTKIPEncryption', 'AESEncryption',
                      'WEPandAESEncryption', 'TKIPandAESEncryption',
                      'WEPandTKIPandAESEncryption']

  AutoChannelEnable = tr.types.Bool(True)
  BasicAuthenticationMode = tr.types.TriggerEnum(
      ['None', 'SharedAuthentication'], init='SharedAuthentication')
  BasicEncryptionModes = tr.types.TriggerEnum(
      ['None', 'WEPEncryption'], init='None')
  BeaconAdvertisementEnabled = tr.types.ReadOnlyBool(True)
  BeaconType = tr.types.TriggerEnum(
      ['None', 'Basic', 'WPA', '11i', 'BasicandWPA', 'Basicand11i', 'WPAand11i',
       'BasicandWPAand11i'], init='11i')
  DeviceOperationMode = tr.types.ReadOnlyString('InfrastructureAccessPoint')
  Enable = tr.types.TriggerBool(False)
  IEEE11iAuthenticationMode = tr.types.TriggerEnum(
      ['PSKAuthentication'], init='PSKAuthentication')
  IEEE11iEncryptionModes = tr.types.TriggerEnum(
      encryption_modes, init='AESEncryption')
  LocationDescription = tr.types.String()
  Name = tr.types.ReadOnlyString()
  # TODO(dgentry): this should be readwrite on GFHD* and read-only on GFRG*
  OperatingFrequencyBand = tr.types.TriggerEnum(['2.4GHz', '5GHz'])
  RadioEnabled = tr.types.TriggerBool(False)
  SSID = tr.types.TriggerString()
  SSIDAdvertisementEnabled = tr.types.TriggerBool(True)
  Standard = tr.types.ReadOnlyString()
  SupportedFrequencyBands = tr.types.ReadOnlyString('2.4GHz,5GHz')
  TransmitPowerSupported = tr.types.ReadOnlyString('0,20,40,60,80,100')
  UAPSDSupported = tr.types.ReadOnlyBool(False)
  WEPEncryptionLevel = tr.types.ReadOnlyString('Disabled,40-bit,104-bit')
  WEPKeyIndex = tr.types.Unsigned(1)
  WMMSupported = tr.types.ReadOnlyBool(False)
  WPAAuthenticationMode = tr.types.TriggerEnum(
      ['PSKAuthentication'], init='PSKAuthentication')
  WPAEncryptionModes = tr.types.TriggerEnum(
      encryption_modes, init='AESEncryption')

  def __init__(self, ifname, standard='n'):
    super(WlanConfiguration, self).__init__()
    self._ifname = ifname
    type(self).Name.Set(self, ifname)
    # TODO(dgentry): can /bin/wifi tell us the capability of the chipset?
    type(self).Standard.Set(self, standard)
    self.force_channel = 1

    # Need to be implemented, but not done yet.
    self.Unexport(['RegulatoryDomain', 'BasicDataTransmitRates',
                   'AutoRateFallBackEnabled', 'OperationalDataTransmitRates',
                   'PossibleChannels', 'TransmitPower', 'TotalAssociations',
                   ])
    self.Unexport(lists=['AssociatedDevice'])

    # Unimplemented, but not yet evaluated
    self.Unexport(['Alias', 'ChannelsInUse', 'MaxBitRate',
                   'PossibleDataTransmitRates',
                   'TotalIntegrityFailures', 'TotalPSKFailures'])

    self.PreSharedKeyList = {}
    for i in range(1, 11):
      self.PreSharedKeyList[str(i)] = wifi.PreSharedKey98()

    self.WEPKeyList = {}
    for i in range(1, 5):
      self.WEPKeyList[str(i)] = wifi.WEPKey98()

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

  @property
  def BSSID(self):
    # TODO(dgentry): /bin/wifi needs to implement queries for various state
    return '00:00:00:00:00:00'

  def GetChannel(self):
    # TODO(dgentry): /bin/wifi needs to implement queries for various state
    return 0

  def ValidateChannel(self, value):
    """Check for a valid Wifi channel number."""
    # TODO(dgentry) can /bin/wifi do this? It knows the regulatory domain.
    if value in range(1, 14):
      return True  # 2.4 GHz. US allows 1-11, Japan allows 1-13.
    if value in range(36, 144, 4):
      return True  # 5 GHz lower bands
    if value in range(149, 169, 4):
      return True  # 5 GHz upper bands
    return False

  def SetChannel(self, value):
    ivalue = int(value)
    if not self.ValidateChannel(ivalue):
      raise ValueError('Invalid Channel: %d' % ivalue)
    self.force_channel = ivalue
    self.AutoChannelEnable = False
    self.Triggered()

  Channel = property(GetChannel, SetChannel, None, 'WLANConfiguration.Channel')

  def GetKeyPassphrase(self):
    psk = self.PreSharedKeyList['1']
    return psk.KeyPassphrase

  def SetKeyPassphrase(self, value):
    psk = self.PreSharedKeyList['1']
    psk.KeyPassphrase = value
    # TODO(dgentry) need to set WEPKeys, but this is fraught with peril.
    # If KeyPassphrase is not exactly 5 or 13 bytes it must be padded.
    # Apple uses different padding than Windows (and others).
    # http://support.apple.com/kb/HT1344

  KeyPassphrase = property(GetKeyPassphrase, SetKeyPassphrase, None,
                           'WLANConfiguration.KeyPassphrase')

  @SSID.validator
  def ValidateSSID(self, value):
    svalue = str(value)
    if len(svalue) > 32:
      raise ValueError('SSID must be <= 32 characters')
    return svalue

  @property
  def Stats(self):
    return WlanConfigurationStats(ifname=self._ifname)

  @property
  def Status(self):
    """WLANConfiguration.Status."""
    if not self._IsConfigComplete():
      return 'Error'
    # TODO(dgentry): get /bin/wifi to return a status.
    return 'Up'

  @property
  def TotalBytesReceived(self):
    return self.Stats.BytesReceived

  @property
  def TotalBytesSent(self):
    return self.Stats.BytesSent

  @property
  def TotalPacketsReceived(self):
    return self.Stats.PacketsReceived

  @property
  def TotalPacketsSent(self):
    return self.Stats.PacketsSent

  @WEPKeyIndex.validator
  def ValidateWEPKeyIndex(self, value):
    ivalue = int(value)
    if ivalue < 1 or ivalue > 4:
      raise ValueError('WEPKeyIndex must be in the range 1-4')
    return ivalue

  def Triggered(self):
    """Called when a parameter is modified."""
    self.UpdateBinWifi()

  def _IsConfigComplete(self):
    """Returns true if configuration is ready to be applied."""
    if not self.SSID:
      return False
    return True

  def _GetEncryptionMode(self):
    """Return /bin/wifi -e argument.

    Args:
      beacon: the BeaconType, either 11i or WPA or Basic
      crypto: the EncryptionMode, like AESEncryption

    Returns:
      The -e argument to pass to /bin/wifi.
    """
    if 'Basic' in self.BeaconType:
      return '-e WEP' if 'WEP' in crypto else '-e NONE'

    if '11i' in self.BeaconType:
      auth = 'WPA2'
      encryption = self.IEEE11iEncryptionModes
    elif 'WPA' in self.BeaconType:
      auth = 'WPA'
      encryption = self.WPAEncryptionModes
    else:
      print 'Invalid BeaconType %s using WPA2' % self.BeaconType
      auth = 'WPA2'
      encryption = self.IEEE11iEncryptionModes

    if 'None' in encryption:
      return '-e NONE'

    if 'AES' in encryption:
      crypto = '_PSK_AES'
    elif 'TKIP' in encryption:
      crypto = '_PSK_TKIP'
    else:
      print 'Invalid EncryptionMode %s, using AES' % crypto
      crypto = '_PSK_AES'

    return '-e ' + auth + crypto

  @tr.mainloop.WaitUntilIdle
  def UpdateBinWifi(self):
    if not self._IsConfigComplete():
      return
    if not self.RadioEnabled:
      # TODO(dgentry): need to be able to turn the radio off
      print 'Unable to turn Radio off'
      return
    if not self.SSIDAdvertisementEnabled:
      # TODO(dgentry): need to be able to turn the beacon off
      print 'Unable to disable SSID Advertisement'
    ch = '-c auto' if self.AutoChannelEnable else '-c %d' % self.force_channel
    ss = '-s %s' % self.SSID
    en = self._GetEncryptionMode()
    cmd = BINWIFI + ['set', '-b', '2.4', ch, ss, en]
    try:
      subprocess.check_call(cmd)
    except (IOError, OSError, subprocess.CalledProcessError):
      print 'Unable to configure Wifi.'
      traceback.print_exc()


class WlanConfigurationStats(netdev.NetdevStatsLinux26, BASE98WIFI.Stats):
  """tr98 InternetGatewayDevice.LANDevice.WLANConfiguration.Stats."""

  def __init__(self, ifname):
    netdev.NetdevStatsLinux26.__init__(self, ifname)
    BASE98WIFI.Stats.__init__(self)

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

import os
import subprocess
import traceback
import tr.cwmpbool
import tr.mainloop
import tr.session
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


class WifiConfig(object):
  """A dumb data object to store config settings."""
  pass


class WlanConfiguration(CATA98WIFI):
  """An implementation of tr98 WLANConfiguration for /bin/wifi."""
  encryption_modes = ['X_CATAWAMPUS-ORG_None', 'None', 'WEPEncryption',
                      'TKIPEncryption', 'WEPandTKIPEncryption', 'AESEncryption',
                      'WEPandAESEncryption', 'TKIPandAESEncryption',
                      'WEPandTKIPandAESEncryption']

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

  def __init__(self, ifname, band='5', standard='n'):
    super(WlanConfiguration, self).__init__()
    self._ifname = ifname
    self._band = band
    type(self).Name.Set(self, ifname)
    # TODO(dgentry): can /bin/wifi tell us the capability of the chipset?
    type(self).Standard.Set(self, standard)
    self.new_config = None

    # Need to be implemented, but not done yet.
    self.Unexport(['BasicDataTransmitRates', 'AutoRateFallBackEnabled',
                   'OperationalDataTransmitRates',
                   'PossibleChannels', 'TransmitPower',
                   ])

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

  def _ParseBinwifiOutput(self, lines):
    """Parse output of /bin/wifi show.

      Example:
        GSAFSJ1234E0123# wifi show
        Band: 5
        RegDomain: US
        BSSID: 00:00:01:02:03:04
        SSID: GFRG_GSAFSJ1234E0123_11ac
        Channel: 153
        Station List for band: 5
        Station 00:00:01:00:00:01 (on wlan0)
                inactive time:  1 ms
                rx bytes:       2
                rx packets:     3
                tx bytes:       4
                tx packets:     5
                tx retries:     6
                tx failed:      7
                signal:         -8 dBm
                signal avg:     -9 dBm
                tx bitrate:     10.0 MBit/s
                rx bitrate:     11.0 MBit/s

      Returns:
        A dict populated with parameter names.
        The dict will contain a AssociatedDevices
        key, which holds a list of dicts (one per
        associated Wifi client).
    """

    rc = {}
    stations = []
    in_stations = False
    for line in lines:
      if 'Station List' in line:
        in_stations = True
        continue
      if not line.strip():
        in_stations = False
        continue

      if in_stations:
        if line.startswith('Station '):
          stations.append(dict())
          fields = line.split(' ')
          stations[-1]['PhysAddr'] = fields[1]
        else:
          param, val = line.split(':', 1)
          stations[-1][param.strip()] = val.strip()
      else:
        param, val = line.split(':', 1)
        rc[param.strip()] = val.strip()
    rc['AssociatedDevices'] = stations
    return rc

  @tr.session.cache
  def _BinwifiShow(self):
    """Cache the output of /bin/wifi show."""
    cmd = BINWIFI + ['show', '-b', self._band]
    try:
      w = subprocess.Popen(cmd, stdout=subprocess.PIPE)
      out, _ = w.communicate(None)
    except (IOError, OSError, subprocess.CalledProcessError):
      print 'Unable to run ' + ' '.join(cmd)
      traceback.print_exc()
      return {}
    return self._ParseBinwifiOutput(out.splitlines())

  def StartTransaction(self):
    """Returns a dict of config updates to be applied."""
    self.new_config = WifiConfig()
    self.new_config.AutoChannelType = self.X_CATAWAMPUS_ORG_AutoChanType
    self.new_config.AutoChannelEnable = self.AutoChannelEnable
    self.new_config.Channel = self.Channel
    self.new_config.SSID = self.SSID

  @property
  @tr.session.cache
  def AssociatedDeviceList(self):
    show = self._BinwifiShow()
    alist = show.get('AssociatedDevices', [])
    result = {}
    for idx, device in enumerate(alist, start=1):
      result[str(idx)] = AssociatedDevice(device)
    return result

  def GetAutoChannelEnable(self):
    d = self._BinwifiShow()
    return True if d.get('AutoChannel', 'TRUE') == 'TRUE' else False

  def SetAutoChannelEnable(self, value):
    b = tr.cwmpbool.parse(value)
    self.new_config.AutoChannelEnable = b
    self.Triggered()

  AutoChannelEnable = property(GetAutoChannelEnable, SetAutoChannelEnable, None,
                               'WLANConfiguration.AutoChannelEnable')

  @property
  def BSSID(self):
    d = self._BinwifiShow()
    return d.get('BSSID', '')

  def GetChannel(self):
    d = self._BinwifiShow()
    return d.get('Channel', '')

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
    self.new_config.Channel = ivalue
    self.AutoChannelEnable = 'False'
    self.Triggered()

  Channel = property(GetChannel, SetChannel, None, 'WLANConfiguration.Channel')

  def GetKeyPassphrase(self):
    psk = self.PreSharedKeyList['1']
    return psk.KeyPassphrase

  def SetKeyPassphrase(self, value):
    psk = self.PreSharedKeyList['1']
    psk.PreSharedKey = value
    # TODO(dgentry) need to set WEPKeys, but this is fraught with peril.
    # If KeyPassphrase is not exactly 5 or 13 bytes it must be padded.
    # Apple uses different padding than Windows (and others).
    # http://support.apple.com/kb/HT1344

  KeyPassphrase = property(GetKeyPassphrase, SetKeyPassphrase, None,
                           'WLANConfiguration.KeyPassphrase')

  @property
  def RegulatoryDomain(self):
    return self._BinwifiShow().get('RegDomain', '').strip()

  def GetSSID(self):
    return self._BinwifiShow().get('SSID', '').strip()

  def ValidateSSID(self, value):
    if len(value) > 32:
      raise ValueError('SSID must be <= 32 characters')
    return value

  def SetSSID(self, value):
    value = str(value)
    if not self.ValidateSSID(value):
      raise ValueError('Invalid SSID: %s' % value)
    self.new_config.SSID = value
    self.Triggered()

  SSID = property(GetSSID, SetSSID, None, 'WLANConfiguration.SSID')

  @property
  def Stats(self):
    return WlanConfigurationStats(ifname=self._ifname)

  @property
  def Status(self):
    """WLANConfiguration.Status."""
    if not self.SSID:
      return 'Error'
    # TODO(dgentry): get /bin/wifi to return a status.
    return 'Up'

  @property
  def TotalAssociations(self):
    return len(self.AssociatedDeviceList)

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

  def GetAutoChanType(self):
    return self._BinwifiShow().get('AutoType', '').strip()

  def SetAutoChanType(self):
    self.new_config.AutoChannelType = tr.cwmpbool.parse(value)

  X_CATAWAMPUS_ORG_AutoChanType = property(
      GetAutoChanType, SetAutoChanType, None,
      'WLANConfiguration.X_CATAWAMPUS-ORG_AutoChanType')

  def Triggered(self):
    """Called when a parameter is modified."""
    self.UpdateBinWifi()

  def _IsConfigComplete(self):
    """Returns true if configuration is ready to be applied."""
    if not self.new_config.SSID:
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
      return 'WEP' if 'WEP' in crypto else 'NONE'

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
      return 'NONE'

    if 'AES' in encryption:
      crypto = '_PSK_AES'
    elif 'TKIP' in encryption:
      crypto = '_PSK_TKIP'
    else:
      print 'Invalid EncryptionMode %s, using AES' % crypto
      crypto = '_PSK_AES'

    return auth + crypto

  @tr.mainloop.WaitUntilIdle
  def UpdateBinWifi(self):
    if not self.RadioEnabled:
      # TODO(dgentry): need to be able to turn the radio off
      print 'Unable to turn Radio off'
      return
    if not self.SSIDAdvertisementEnabled:
      # TODO(dgentry): need to be able to turn the beacon off
      print 'Unable to disable SSID Advertisement'
    cmd = BINWIFI + ['set', '-b', self._band, '-e', self._GetEncryptionMode()]
    env = os.environ.copy()
    ae = self.new_config.AutoChannelEnable
    ch = 'auto' if ae else str(self.new_config.Channel)
    if ch:
      cmd += ['-c', ch]
    ssid = self.new_config.SSID
    if ssid:
      cmd += ['-s', ssid]
    autotype = self.new_config.AutoChannelType
    if autotype:
      cmd += ['-a', autotype]
    for psk in self.PreSharedKeyList.values():
      if psk.PreSharedKey:
        env['WIFI_PSK'] = psk.PreSharedKey
        break

    try:
      print 'Running %s' % str(cmd)
      child = subprocess.Popen(cmd, env=env, close_fds=True, shell=False)
      child.wait()
    except (IOError, OSError, subprocess.CalledProcessError):
      print 'Unable to configure Wifi.'
      traceback.print_exc()


class WlanConfigurationStats(netdev.NetdevStatsLinux26, BASE98WIFI.Stats):
  """tr98 InternetGatewayDevice.LANDevice.WLANConfiguration.Stats."""

  def __init__(self, ifname):
    netdev.NetdevStatsLinux26.__init__(self, ifname)
    BASE98WIFI.Stats.__init__(self)


class AssociatedDevice(CATA98WIFI.AssociatedDevice):
  """InternetGatewayDevice.LANDevice.WLANConfiguration.AssociatedDevice."""

  AssociatedDeviceAuthenticationState = tr.types.ReadOnlyBool(True)
  AssociatedDeviceMACAddress = tr.types.ReadOnlyMacAddr()
  # tr-098-1-6 defines LastDataTransmitRate as a string(4). Bizarre.
  LastDataTransmitRate = tr.types.ReadOnlyString()
  X_CATAWAMPUS_ORG_Active = tr.types.ReadOnlyBool(False)
  X_CATAWAMPUS_ORG_LastDataDownlinkRate = tr.types.ReadOnlyUnsigned()
  X_CATAWAMPUS_ORG_LastDataUplinkRate = tr.types.ReadOnlyUnsigned()
  X_CATAWAMPUS_ORG_SignalStrength = tr.types.ReadOnlyInt()
  X_CATAWAMPUS_ORG_SignalStrengthAverage = tr.types.ReadOnlyInt()

  def __init__(self, device):
    super(AssociatedDevice, self).__init__()
    type(self).AssociatedDeviceMACAddress.Set(self, device.get('PhysAddr', ''))
    idle_ms = int(device.get('inactive time', '0 ms').split()[0])
    if idle_ms < 120000:
      type(self).X_CATAWAMPUS_ORG_Active.Set(self, True)

    bitrate = float(device.get('tx bitrate', '0.0 MBit/s').split()[0])
    kbps = int(bitrate * 1000.0)
    type(self).X_CATAWAMPUS_ORG_LastDataUplinkRate.Set(self, kbps)

    bitrate = float(device.get('rx bitrate', '0.0 MBit/s').split()[0])
    kbps = int(bitrate * 1000.0)
    mbps = int(bitrate)
    type(self).X_CATAWAMPUS_ORG_LastDataDownlinkRate.Set(self, kbps)
    type(self).LastDataTransmitRate.Set(self, mbps)

    dbm = int(device.get('signal', '0 dBm').split()[0])
    type(self).X_CATAWAMPUS_ORG_SignalStrength.Set(self, dbm)
    dbm = int(device.get('signal avg', '0 dBm').split()[0])
    type(self).X_CATAWAMPUS_ORG_SignalStrengthAverage.Set(self, dbm)

    self.Unexport(['AssociatedDeviceIPAddress', 'LastPMKId',
                   'LastRequestedUnicastCipher',
                   'LastRequestedMulticastCipher'])

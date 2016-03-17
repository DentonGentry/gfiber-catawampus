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
# pylint: disable=invalid-name

"""Implementation of tr-98 WLAN objects for /bin/wifi.

The platform code is expected to set the BSSID (which is really a MAC address).
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import errno
import json
import os
import subprocess
import time
import traceback
import netdev
import tornado.ioloop
import tr.cwmpbool
import tr.cwmptypes
import tr.experiment
import tr.helpers
import tr.mainloop
import tr.pyinotify
import tr.session
import tr.tr098_v1_6
import tr.x_catawampus_tr098_1_0

BASE98IGD = tr.tr098_v1_6.InternetGatewayDevice_v1_12.InternetGatewayDevice
BASE98WIFI = BASE98IGD.LANDevice.WLANConfiguration
CATA98 = tr.x_catawampus_tr098_1_0.X_CATAWAMPUS_ORG_InternetGatewayDevice_v1_0
CATA98WIFI = CATA98.InternetGatewayDevice.LANDevice.WLANConfiguration
ISOSTREAM_KEY = 'Device.X_CATAWAMPUS-ORG.Isostream.'

# Unit tests can override these.
BINWIFI = ['wifi']
CONMAN_DIR = ['/config/conman']
STATIONS_DIR = ['/tmp/stations']
TMPWAVEGUIDE = ['/tmp/waveguide']
WIFIINFO_DIR = ['/tmp/wifi/wifiinfo']


class WifiConfig(object):
  """A dumb data object to store config settings."""
  pass


def _WifiConfigs(roothandle):
  try:
    landevices = roothandle.obj.InternetGatewayDevice.LANDeviceList
  except AttributeError as e:
    print '_WifiConfigs: %r' % e
    return

  for lann, lan in landevices.iteritems():
    try:
      wlanconfigs = lan.WLANConfigurationList
    except AttributeError:
      pass
    for wlann, wlan in wlanconfigs.iteritems():
      yield ('InternetGatewayDevice.LANDevice.%s.WLANConfiguration.%s.'
             % (lann, wlann)), wlan


@tr.experiment.Experiment
def AutoDisableWifi(roothandle):
  for wlankey, wlan in _WifiConfigs(roothandle):
    if hasattr(wlan, 'X_CATAWAMPUS_ORG_AllowAutoDisable'):
      yield (wlankey + 'X_CATAWAMPUS-ORG_AllowAutoDisable'), True


@tr.experiment.Experiment
def AlwaysEnableSetupNetwork(unused_roothandle):
  # TODO(willangley): also enable setup network on 5 GHz once the ACS pushes
  #   configuration for it, too.
  yield 'InternetGatewayDevice.LANDevice.2.WLANConfiguration.1.Enable', True
  yield ('InternetGatewayDevice.LANDevice.2.WLANConfiguration.1'
         '.SSIDAdvertisementEnabled', True)


@tr.experiment.Experiment
def WaveguideInitialChannel(roothandle):
  for wlankey, wlan in _WifiConfigs(roothandle):
    yield (wlankey + 'AutoChannelEnable'), True
    if hasattr(wlan, 'X_CATAWAMPUS_ORG_AutoChannelAlgorithm'):
      yield (wlankey + 'X_CATAWAMPUS-ORG_AutoChannelAlgorithm'), 'INITIAL'


@tr.experiment.Experiment
def WaveguideDynamicChannel(roothandle):
  for wlankey, wlan in _WifiConfigs(roothandle):
    yield (wlankey + 'AutoChannelEnable'), True
    if hasattr(wlan, 'X_CATAWAMPUS_ORG_AutoChannelAlgorithm'):
      yield (wlankey + 'X_CATAWAMPUS-ORG_AutoChannelAlgorithm'), 'DYNAMIC'


@tr.experiment.Experiment
def Wifi24GForce40M(roothandle):
  for wlankey, wlan in _WifiConfigs(roothandle):
    if hasattr(wlan, 'X_CATAWAMPUS_ORG_Width24G'):
      yield (wlankey + 'X_CATAWAMPUS-ORG_Width24G'), '40'


@tr.experiment.Experiment
def Wifi5GForce20M(roothandle):
  for wlankey, wlan in _WifiConfigs(roothandle):
    if hasattr(wlan, 'X_CATAWAMPUS_ORG_Width5G'):
      yield (wlankey + 'X_CATAWAMPUS-ORG_Width5G'), '20'


@tr.experiment.Experiment
def Wifi5GForce40M(roothandle):
  for wlankey, wlan in _WifiConfigs(roothandle):
    if hasattr(wlan, 'X_CATAWAMPUS_ORG_Width5G'):
      yield (wlankey + 'X_CATAWAMPUS-ORG_Width5G'), '40'


@tr.experiment.Experiment
def Wifi5GDisable(roothandle):
  for wlankey, wlan in _WifiConfigs(roothandle):
    if getattr(wlan, '_fixed_band', '') == '5':
      yield (wlankey + 'Enable'), False


@tr.experiment.Experiment
def WifiShortGuardInterval(roothandle):
  for wlankey, wlan in _WifiConfigs(roothandle):
    if hasattr(wlan, 'GuardInterval'):
      yield (wlankey + 'GuardInterval'), '400nsec'


@tr.experiment.Experiment
def WifiDisableWMM(roothandle):
  """Note: only applies if not using 802.11n or later."""
  for wlankey, wlan in _WifiConfigs(roothandle):
    if hasattr(wlan, 'WMMEnable'):
      yield (wlankey + 'WMMEnable'), False


@tr.experiment.Experiment
def WifiRekeyNever(roothandle):
  for wlankey, wlan in _WifiConfigs(roothandle):
    if hasattr(wlan, 'RekeyingInterval'):
      yield (wlankey + 'RekeyingInterval'), 0


@tr.experiment.Experiment
def WifiRekeyPTK(roothandle):
  for wlankey, wlan in _WifiConfigs(roothandle):
    if hasattr(wlan, 'RekeyingInterval'):
      yield (wlankey + 'RekeyingInterval'), 1


@tr.experiment.Experiment
def WifiRekeyOften(roothandle):
  for wlankey, wlan in _WifiConfigs(roothandle):
    if hasattr(wlan, 'RekeyingInterval'):
      yield (wlankey + 'RekeyingInterval'), 10


@tr.experiment.Experiment
def Wifi80211g(roothandle):
  for wlankey, wlan in _WifiConfigs(roothandle):
    if hasattr(wlan, 'X_CATAWAMPUS_ORG_Width24G'):
      yield (wlankey + 'X_CATAWAMPUS-ORG_Width24G'), '20'
    if hasattr(wlan, 'X_CATAWAMPUS_ORG_Width5G'):
      yield (wlankey + 'X_CATAWAMPUS-ORG_Width5G'), '20'
    yield (wlankey + 'Standard'), 'g'


@tr.experiment.Experiment
def Wifi24G80211g(roothandle):
  for wlankey, wlan in _WifiConfigs(roothandle):
    # Note: this intentionally doesn't match dual-band interfaces, because
    # there's no clean way to switch this back in 5 GHz mode on those.
    if hasattr(wlan, 'X_CATAWAMPUS_ORG_Width24G'):
      yield (wlankey + 'X_CATAWAMPUS-ORG_Width24G'), '20'
    if getattr(wlan, '_fixed_band', '') == '2.4':
      yield (wlankey + 'Standard'), 'g'


@tr.experiment.Experiment
def ForceTvBoxWifi(roothandle):
  try:
    model_name = roothandle.obj.Device.DeviceInfo.ModelName
  except AttributeError as e:
    print 'ForceTvBoxWifi: %r' % e
    return
  if not model_name.startswith('GFHD'):
    print 'ForceTvBoxWifi: %r is not a TV box.  skipping.' % model_name
    return
  for wlankey, unused_wlan in _WifiConfigs(roothandle):
    yield wlankey + 'Enable', True
    yield wlankey + 'RadioEnabled', True


@tr.experiment.Experiment
def ForceNoTvBoxWifi(roothandle):
  try:
    model_name = roothandle.obj.Device.DeviceInfo.ModelName
  except AttributeError as e:
    print 'ForceNoTvBoxWifi: %r' % e
    return
  if not model_name.startswith('GFHD'):
    print 'ForceNoTvBoxWifi: %r is not a TV box.  skipping.' % model_name
    return
  for wlankey, unused_wlan in _WifiConfigs(roothandle):
    yield wlankey + 'Enable', False
    yield wlankey + 'RadioEnabled', False


@tr.experiment.Experiment
def ForceTvBoxWifiClient(roothandle):
  """Force join the wireless network provided by the InternetGatewayDevice."""

  try:
    model_name = roothandle.obj.Device.DeviceInfo.ModelName
  except AttributeError as e:
    print 'ForceTvBoxWifiClient: %r' % e
    return

  if not model_name.startswith('GFHD'):
    print 'ForceTvBoxWifiClient: %r is not a TV box. Skipping.' % model_name
    return

  for wlankey, wlan in _WifiConfigs(roothandle):
    if hasattr(wlan, 'ClientEnable'):
      yield wlankey + 'RadioEnabled', True
      yield wlankey + 'Enable', False
      yield wlankey + 'ClientEnable', True
      yield ISOSTREAM_KEY + 'ClientInterface', 'wcli0'
      yield ISOSTREAM_KEY + 'ClientDisableIfPortActive', 0
      return  # ensure we only try to associate with one WLAN

  print 'ForceTvBoxWifiClient: %r does not support .ClientEnable' % model_name


def _FreqToChan(mhz):
  if mhz / 100 == 24:
    return 1 + (mhz - 2412) / 5
  elif mhz / 1000 == 5:
    return 36 + (mhz - 5180) / 5
  else:
    print 'invalid wifi frequency: %r' % (mhz,)
    return 0


class _SoftInt(tr.cwmptypes.Int):
  """Like tr.cwmptypes.Int, but converts invalid values to zero."""

  def validate(self, obj, value):
    try:
      value = int(value)
    except (TypeError, ValueError):
      value = 0
    return super(_SoftInt, self).validate(obj, value)


class _SoftBool(tr.cwmptypes.Bool):
  """Like tr.cwmptypes.Bool, but any value (even empty) is true."""

  def validate(self, obj, value):
    # A file which exists but is empty is true.
    return value is not None


class StationsChangeHandler(tr.pyinotify.ProcessEvent):
  """Handler for processing changes to the /tmp/stations directory."""

  def __init__(self, wlanconfig):
    self.wlanconfig = wlanconfig

  def process_IN_CREATE(self, event):
    self.wlanconfig.AssocDeviceListMaker()

  def process_IN_MODIFY(self, event):
    self.wlanconfig.AssocDeviceListMaker()

  def process_IN_DELETE(self, event):
    wlan = self.wlanconfig
    wlan.AssocDeviceListMaker()
    if not wlan.AssociatedDeviceList:
      wlan.signals = {}


class WlanConfiguration(CATA98WIFI):
  """An implementation of tr98 WLANConfiguration for /bin/wifi."""
  encryption_modes = ['X_CATAWAMPUS-ORG_None', 'None', 'WEPEncryption',
                      'TKIPEncryption', 'WEPandTKIPEncryption', 'AESEncryption',
                      'WEPandAESEncryption', 'TKIPandAESEncryption',
                      'WEPandTKIPandAESEncryption']

  BasicAuthenticationMode = tr.cwmptypes.TriggerEnum(
      ['None', 'SharedAuthentication'], init='SharedAuthentication')
  BasicEncryptionModes = tr.cwmptypes.TriggerEnum(
      ['None', 'WEPEncryption'], init='None')
  BeaconAdvertisementEnabled = tr.cwmptypes.ReadOnlyBool(True)
  BeaconType = tr.cwmptypes.TriggerEnum(
      ['None', 'Basic', 'WPA', '11i', 'BasicandWPA', 'Basicand11i', 'WPAand11i',
       'BasicandWPAand11i'], init='11i')
  ClientEnable = tr.cwmptypes.TriggerBool(False)
  DeviceOperationMode = tr.cwmptypes.ReadOnlyString('InfrastructureAccessPoint')
  Enable = tr.cwmptypes.TriggerBool(False)
  GuardInterval = tr.cwmptypes.TriggerEnum(
      ['400nsec', '800nsec', 'Auto'], init='Auto')
  IEEE11iAuthenticationMode = tr.cwmptypes.TriggerEnum(
      ['PSKAuthentication'], init='PSKAuthentication')
  IEEE11iEncryptionModes = tr.cwmptypes.TriggerEnum(
      encryption_modes, init='AESEncryption')
  LocationDescription = tr.cwmptypes.String()
  Name = tr.cwmptypes.ReadOnlyString()
  RadioEnabled = tr.cwmptypes.TriggerBool(False)
  RekeyingInterval = tr.cwmptypes.TriggerUnsigned(3600)
  SSIDAdvertisementEnabled = tr.cwmptypes.TriggerBool(True)
  SupportedStandards = tr.cwmptypes.ReadOnlyString()
  OperatingStandards = tr.cwmptypes.TriggerString()
  SupportedFrequencyBands = tr.cwmptypes.ReadOnlyString('2.4GHz,5GHz')
  TransmitPowerSupported = tr.cwmptypes.ReadOnlyString('0,20,40,60,80,100')
  UAPSDSupported = tr.cwmptypes.ReadOnlyBool(False)
  WEPEncryptionLevel = tr.cwmptypes.ReadOnlyString('Disabled,40-bit,104-bit')
  WEPKeyIndex = tr.cwmptypes.Unsigned(1)
  WMMSupported = tr.cwmptypes.ReadOnlyBool(True)
  WMMEnable = tr.cwmptypes.TriggerBool(True)
  WPAAuthenticationMode = tr.cwmptypes.TriggerEnum(
      ['PSKAuthentication'], init='PSKAuthentication')
  WPAEncryptionModes = tr.cwmptypes.TriggerEnum(
      encryption_modes, init='AESEncryption')
  SignalsStr = tr.cwmptypes.ReadOnlyString()

  def __init__(self, ifname, if_suffix, bridge, band=None, standard='n',
               width_2_4g=0, width_5g=0, autochan=None):
    super(WlanConfiguration, self).__init__()
    self._initialized = False
    self._if_suffix = if_suffix
    self._ifname = ifname + if_suffix
    type(self).Name.Set(self, self._ifname)
    self._band = band if band else '5'
    self._bridge = bridge
    self._fixed_band = band
    if standard == 'ac':
      type(self).SupportedStandards.Set(self, 'a,b,g,n,ac')
    elif standard == 'n':
      type(self).SupportedStandards.Set(self, 'a,b,g,n')
    else:
      raise ValueError('unsupported wifi standards level: %r' % (standard,))
    self.Standard = standard
    self.X_CATAWAMPUS_ORG_Width24G = str(width_2_4g) if width_2_4g else ''
    self.X_CATAWAMPUS_ORG_Width5G = str(width_5g) if width_5g else ''
    self._autochan = autochan
    self.new_config = None
    self._Stats = WlanConfigurationStats(ifname=self._ifname)
    self._initialized = True
    self.AssociatedDeviceList = {}
    self._sig_dict = {}
    self.StationsWatchManager = tr.pyinotify.WatchManager()

    # Need to be implemented, but not done yet.
    self.Unexport(['BasicDataTransmitRates', 'AutoRateFallBackEnabled',
                   'OperationalDataTransmitRates',
                   'PossibleChannels', 'TransmitPower'])

    # Unimplemented, but not yet evaluated
    self.Unexport(['Alias', 'ChannelsInUse', 'MaxBitRate',
                   'PossibleDataTransmitRates',
                   'TotalIntegrityFailures', 'TotalPSKFailures'])

    self.PreSharedKeyList = {}
    for i in range(1, 11):
      self.PreSharedKeyList[str(i)] = PreSharedKey(parent=self)

    self.WEPKeyList = {}
    for i in range(1, 5):
      self.WEPKeyList[str(i)] = WEPKey(parent=self)

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
    self.Unexport(['UAPSDEnable'])

    # WDS, currently unimplemented but could be supported at some point.
    self.Unexport(['PeerBSSID', 'DistanceFromRoot'])

    # Waveguide interface
    try:
      os.makedirs(TMPWAVEGUIDE[0], 0755)
    except OSError as e:
      if e.errno != errno.EEXIST:
        raise
    # pylint:disable=protected-access
    type(self).X_CATAWAMPUS_ORG_AutoDisableRecommended.attr.attr.SetFileName(
        self, TMPWAVEGUIDE[0] + '/%s.disabled' % self.Name)
    type(self)._RecommendedChannel_2G.attr.attr.SetFileName(
        self, TMPWAVEGUIDE[0] + '/%s.autochan_2g' % self.Name)
    type(self)._RecommendedChannel_5G.attr.attr.SetFileName(
        self, TMPWAVEGUIDE[0] + '/%s.autochan_5g' % self.Name)
    type(self)._RecommendedChannel_Free.attr.attr.SetFileName(
        self, TMPWAVEGUIDE[0] + '/%s.autochan_free' % self.Name)
    type(self)._InitiallyRecommendedChannel_2G.attr.attr.SetFileName(
        self, TMPWAVEGUIDE[0] + '/%s.autochan_2g.init' % self.Name)
    type(self)._InitiallyRecommendedChannel_5G.attr.attr.SetFileName(
        self, TMPWAVEGUIDE[0] + '/%s.autochan_5g.init' % self.Name)
    type(self)._InitiallyRecommendedChannel_Free.attr.attr.SetFileName(
        self, TMPWAVEGUIDE[0] + '/%s.autochan_free.init' % self.Name)

    # Watcher/Notifier for files being created or deleted in /tmp/stations
    if not os.path.isdir(STATIONS_DIR[0]):
      os.mkdir(STATIONS_DIR[0])
    ioloop = tornado.ioloop.IOLoop.instance()
    mask = tr.pyinotify.IN_CREATE | tr.pyinotify.IN_DELETE
    mask |= tr.pyinotify.IN_MODIFY
    self.Notifier = tr.pyinotify.TornadoAsyncNotifier(self.StationsWatchManager,
                                                      ioloop)
    donefile = os.path.join(STATIONS_DIR[0], 'updated.new')
    self.StationsWatchManager.add_watch(donefile, mask,
                                        proc_fun=StationsChangeHandler(self))

  def release(self):
    tr.helpers.Unlink(self.WifiCommandFileName())
    tr.helpers.Unlink(self.APEnabledFileName())
    self.Notifier.stop()

  @tr.session.cache
  def _BinwifiShow(self):
    wifi_data = {}
    try:
      wifi_data = json.load(open(os.path.join(WIFIINFO_DIR[0], self._ifname)))
      wifi_data['Band'] = self._band
    except (IOError, OSError, subprocess.CalledProcessError):
      print ('Unable to load wifi info from: ' +
             os.path.join(WIFIINFO_DIR[0], self._ifname))
      traceback.print_exc()
      return {}
    return wifi_data

  def StartTransaction(self):
    """Returns a dict of config updates to be applied."""
    if self.new_config is None:
      self.new_config = WifiConfig()
      atype = self.X_CATAWAMPUS_ORG_AutoChanType
      self.new_config.AutoChannelType = self._autochan or atype
      self.new_config.AutoChannelEnable = self.AutoChannelEnable
      self.new_config.Channel = self.Channel
      self.new_config.SSID = self.SSID

  @property
  def signals(self):
    return self._sig_dict

  @signals.setter
  def signals(self, new_dict):
    self._sig_dict = new_dict
    type(self).SignalsStr.Set(self, str(self._sig_dict))

  def AssocDeviceListMaker(self):
    directory = STATIONS_DIR[0]
    stations = []
    valid_stations = []
    stations_dict = {}
    if os.path.isdir(directory):
      for dirfile in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, dirfile)):
          if not dirfile.endswith('.new'):
            try:
              device_data = json.load(open(os.path.join(directory, dirfile)))
            except ValueError:
              device_data = {}
            station = dict(PhysAddr=dirfile)
            station.update(device_data)
            stations.append(station)
    for station in stations:
      if (('authorized' in station and station['authorized'] != 'yes') or
          ('authenticated' in station and station['authenticated'] != 'yes')):
        continue
      if station.get('ifname') != self._ifname:
        continue
      valid_stations.append(station)
    stations = valid_stations
    AssociatedDeviceMACs = []
    for device in self.AssociatedDeviceList.values():
      AssociatedDeviceMACs.append(device.AssociatedDeviceMACAddress)
    for idx, device in enumerate(sorted(stations), start=1):
      stations_dict[str(idx)] = device['PhysAddr']
      if device['PhysAddr'] not in AssociatedDeviceMACs:
        ad = AssociatedDevice(device,
                              os.path.join(directory, device['PhysAddr']),
                              self)
        self.AssociatedDeviceList[str(idx)] = ad
    for idx in self.AssociatedDeviceList.keys():  # pylint: disable=g-builtin-op
      mac_addr = self.AssociatedDeviceList[idx].AssociatedDeviceMACAddress
      if mac_addr not in stations_dict.values():
        del self.AssociatedDeviceList[idx]

  def GetAutoChannelEnable(self):
    acalg = self.X_CATAWAMPUS_ORG_AutoChannelAlgorithm
    if acalg == 'LEGACY':
      d = self._BinwifiShow()
      return d.get('AutoChannel', 'TRUE') == 'TRUE'
    else:
      # In non-legacy modes, we're passing an explicit channel to
      # /bin/wifi, so in its mind, we are never using autochannel.
      # Report back the real autochannel setting.
      return self.new_config.AutoChannelEnable

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
    try:
      return int(d.get('Channel', 0))
    except ValueError:
      print 'Failed to convert wifi channel to integer: %s' % (d,)
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
    self.new_config.Channel = ivalue
    self.AutoChannelEnable = 'False'
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

  def _InternalBandToExternal(self, internal):
    return '2.4GHz' if internal == '2.4' else '5GHz'

  def _ExternalBandToInternal(self, external):
    return '2.4' if external == '2.4GHz' else '5'

  def GetOperatingFrequencyBand(self):
    return self._InternalBandToExternal(self._band)

  def SetOperatingFrequencyBand(self, value):
    if str(value) not in ['2.4GHz', '5GHz', '']:
      raise ValueError('Invalid band')
    internal = self._ExternalBandToInternal(str(value))
    if self._fixed_band and self._fixed_band != internal:
      raise AttributeError("can't set read-only attribute")
    else:
      self._band = internal
    self.Triggered()

  OperatingFrequencyBand = property(GetOperatingFrequencyBand,
                                    SetOperatingFrequencyBand, None,
                                    'WLANConfiguration.OperatingFrequencyBand')

  @property
  def Standard(self):
    l = self.OperatingStandards.split(',')
    if 'ac' in l:
      return 'ac'
    elif 'n' in l:
      return 'n'
    elif 'g' in l:
      return 'g'
    else:
      return 'b'

  @Standard.setter
  def Standard(self, v):
    if v == 'ac':
      self.OperatingStandards = 'a,b,g,n,ac'
    elif v == 'n':
      self.OperatingStandards = 'a,b,g,n'
    elif v == 'g':
      self.OperatingStandards = 'a,b,g'
    elif v == 'a' or v == 'b':
      self.OperatingStandards = 'a,b'
    else:
      raise ValueError('unknown wifi standard %r' % (v,))

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
    return self._Stats

  X_CATAWAMPUS_ORG_Width24G = tr.cwmptypes.TriggerEnum(
      ['', '20', '40'], '')
  X_CATAWAMPUS_ORG_Width5G = tr.cwmptypes.TriggerEnum(
      ['', '20', '40', '80'], '')

  X_CATAWAMPUS_ORG_AllowAutoDisable = tr.cwmptypes.TriggerBool(False)

  X_CATAWAMPUS_ORG_AutoDisableRecommended = tr.cwmptypes.Trigger(
      tr.cwmptypes.ReadOnly(
          tr.cwmptypes.FileBacked(
              TMPWAVEGUIDE[0] + '/disabled',  # filename varies
              _SoftBool())))

  X_CATAWAMPUS_ORG_AutoChannelAlgorithm = tr.cwmptypes.TriggerEnum(
      ['LEGACY', 'INITIAL', 'DYNAMIC'], 'LEGACY')

  _RecommendedChannel_2G = tr.cwmptypes.Trigger(
      tr.cwmptypes.ReadOnly(
          tr.cwmptypes.FileBacked(
              TMPWAVEGUIDE[0] + '/autochan_2g',  # filename varies
              _SoftInt())))

  _RecommendedChannel_5G = tr.cwmptypes.Trigger(
      tr.cwmptypes.ReadOnly(
          tr.cwmptypes.FileBacked(
              TMPWAVEGUIDE[0] + '/autochan_5g',  # filename varies
              _SoftInt())))

  _RecommendedChannel_Free = tr.cwmptypes.Trigger(
      tr.cwmptypes.ReadOnly(
          tr.cwmptypes.FileBacked(
              TMPWAVEGUIDE[0] + '/autochan_free',  # filename varies
              _SoftInt())))

  @property
  def X_CATAWAMPUS_ORG_RecommendedChannel(self):
    # TODO(apenwarr): Add some way to express "choose best band automatically".
    #  Waveguide (coordinating with other APs on the LAN) can probably make
    #  better decisions than ACS.  Then we'd use _RecommendedChannel_Free.
    #  For now, we'll just take the ACS's recommendation.
    if self.OperatingFrequencyBand == '2.4GHz':
      return self._RecommendedChannel_2G
    elif self.OperatingFrequencyBand == '5GHz':
      return self._RecommendedChannel_5G

  _InitiallyRecommendedChannel_2G = tr.cwmptypes.Trigger(
      tr.cwmptypes.ReadOnly(
          tr.cwmptypes.FileBacked(
              TMPWAVEGUIDE[0] + '/autochan_2g.init',  # filename varies
              _SoftInt())))

  _InitiallyRecommendedChannel_5G = tr.cwmptypes.Trigger(
      tr.cwmptypes.ReadOnly(
          tr.cwmptypes.FileBacked(
              TMPWAVEGUIDE[0] + '/autochan_5g.init',  # filename varies
              _SoftInt())))

  _InitiallyRecommendedChannel_Free = tr.cwmptypes.Trigger(
      tr.cwmptypes.ReadOnly(
          tr.cwmptypes.FileBacked(
              TMPWAVEGUIDE[0] + '/autochan_free.init',  # filename varies
              _SoftInt())))

  @property
  def X_CATAWAMPUS_ORG_InitiallyRecommendedChannel(self):
    # TODO(apenwarr): Add some way to express "choose best band automatically".
    #  See note in RecommendedChannel above.
    if self.OperatingFrequencyBand == '2.4GHz':
      return self._InitiallyRecommendedChannel_2G
    elif self.OperatingFrequencyBand == '5GHz':
      return self._InitiallyRecommendedChannel_5G

  def _ReallyWantWifi(self):
    return (self.Enable and
            self.RadioEnabled and
            not (self.X_CATAWAMPUS_ORG_AllowAutoDisable and
                 self.X_CATAWAMPUS_ORG_AutoDisableRecommended))

  @property
  def Status(self):
    """WLANConfiguration.Status."""
    if not self._ReallyWantWifi():
      return 'Down'
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

  def SetAutoChanType(self, value):
    self.new_config.AutoChannelType = str(value)

  X_CATAWAMPUS_ORG_AutoChanType = property(
      GetAutoChanType, SetAutoChanType, None,
      'WLANConfiguration.X_CATAWAMPUS-ORG_AutoChanType')

  def Triggered(self):
    """Called when a parameter is modified."""
    if self._initialized:
      self.ExportWifiPolicy()

  def _IsConfigComplete(self):
    """Returns true if configuration is ready to be applied."""
    if not self.new_config.SSID:
      return False
    return True

  def _GetEncryptionMode(self):
    """Return /bin/wifi -e argument.

    Returns:
      The -e argument to pass to /bin/wifi.
    """
    if 'Basic' in self.BeaconType:
      return 'WEP' if 'WEP' in self.BasicEncryptionModes else 'NONE'

    if 'WPAand11i' in self.BeaconType:
      auth = 'WPA12'
      encryption = self.WPAEncryptionModes
    elif '11i' in self.BeaconType:
      auth = 'WPA2'
      encryption = self.IEEE11iEncryptionModes
    elif 'WPA' in self.BeaconType:
      auth = 'WPA'
      encryption = self.WPAEncryptionModes
    else:
      print 'Invalid BeaconType %s, using WPA2' % self.BeaconType
      auth = 'WPA2'
      encryption = self.IEEE11iEncryptionModes

    if 'None' in encryption:
      return 'NONE'

    if 'AES' in encryption:
      crypto = '_PSK_AES'
    elif 'TKIP' in encryption:
      crypto = '_PSK_TKIP'
    else:
      print 'Invalid EncryptionMode %s, using AES' % encryption
      crypto = '_PSK_AES'

    return auth + crypto

  def _MakeBinWifiCommand(self):
    """Return command to run /bin/wifi."""
    if self.new_config is None:
      print '_MakeBinWifiCommand: WiFi configuration not yet received.'
      return ''

    cmd = ['set', '-P', '-b', self._band, '-e', self._GetEncryptionMode()]
    if self._if_suffix:
      cmd += ['--interface-suffix=%s' % self._if_suffix]

    cmd += ['--bridge=%s' % self._bridge or '']

    if not self.SSIDAdvertisementEnabled:
      cmd += ['-H']
    if self.new_config.AutoChannelEnable:
      acalg = self.X_CATAWAMPUS_ORG_AutoChannelAlgorithm
      if acalg == 'INITIAL':
        ch = _FreqToChan(self.X_CATAWAMPUS_ORG_InitiallyRecommendedChannel)
      elif acalg == 'DYNAMIC':
        ch = _FreqToChan(self.X_CATAWAMPUS_ORG_RecommendedChannel)
      else:  # LEGACY
        ch = 'auto'
    else:
      ch = self.new_config.Channel
    if ch:
      cmd += ['-c', str(ch)]
    ssid = self.new_config.SSID
    if ssid:
      cmd += ['-s', ssid]
    autotype = self.new_config.AutoChannelType
    if autotype:
      cmd += ['-a', autotype]

    cw24 = self.X_CATAWAMPUS_ORG_Width24G
    cw5 = self.X_CATAWAMPUS_ORG_Width5G
    if self._band == '2.4' and cw24:
      cmd += ['-w', cw24]
    elif self._band == '5' and cw5:
      cmd += ['-w', cw5]

    cmd += ['-p', '/'.join(self.OperatingStandards.split(',')).encode('utf8')]

    if self.Standard in ('n', 'ac') or self.WMMEnable:
      cmd += ['-M']

    if self.RekeyingInterval == 1:
      cmd += ['-X']  # normal rekeying but add PTK rekeying
    elif self.RekeyingInterval == 0:
      cmd += ['-Y']  # disable all rekeying
    elif self.RekeyingInterval <= 300:
      cmd += ['-XX']  # very fast rekeying

    if self.GuardInterval == '400nsec':
      cmd += ['-G']

    def validate(s):
      if '\0' in s:
        raise ValueError('string %r contains a NUL character' % s)
      if '\n' in s:
        raise ValueError('string %r contains a newline character' % s)
      if '\r' in s:
        raise ValueError('string %r contains a carriage return character' % s)

      return s

    wifi_psk = []
    sl = sorted(self.PreSharedKeyList.iteritems(), key=lambda x: int(x[0]))
    for (_, psk) in sl:
      key = psk.GetKey()
      if key:
        wifi_psk = ['env', 'WIFI_PSK=%s' % validate(key)]
        break
    return '\n'.join(wifi_psk + BINWIFI + [validate(token) for token in cmd])

  def _ConmanFileName(self, prefix):
    if_suffix = ('%s.' % self._if_suffix) if self._if_suffix else ''
    return os.path.join(CONMAN_DIR[0],
                        '%s.%s%s' % (prefix, if_suffix, self._band))

  def WifiCommandFileName(self):
    return self._ConmanFileName('command')

  def APEnabledFileName(self):
    return self._ConmanFileName('access_point')

  @tr.mainloop.WaitUntilIdle
  def ExportWifiPolicy(self):
    """Export /bin/wifi command and wifi policy."""
    if not os.path.exists(CONMAN_DIR[0]):
      os.makedirs(CONMAN_DIR[0])

    tr.helpers.WriteFileAtomic(self.WifiCommandFileName(),
                               self._MakeBinWifiCommand())

    ap_enabled_filename = self.APEnabledFileName()
    if self._ReallyWantWifi():
      with open(ap_enabled_filename, 'w'):
        pass
    else:
      tr.helpers.Unlink(ap_enabled_filename)


class PreSharedKey(BASE98WIFI.PreSharedKey):
  """InternetGatewayDevice.WLANConfiguration.{i}.PreSharedKey.{i}."""

  def __init__(self, parent):
    super(PreSharedKey, self).__init__()
    self.Unexport(['Alias', 'PreSharedKey', 'AssociatedDeviceMACAddress'])
    self.passphrase = ''
    self.parent = parent

  def Triggered(self):
    self.parent.Triggered()

  def GetKey(self):
    """Return the key to program into the Wifi chipset."""
    return self.passphrase

  def SetKeyPassphrase(self, value):
    self.passphrase = str(value)
    self.Triggered()

  def GetKeyPassphrase(self):
    """tr98 says KeyPassphrase always reads back an empty value."""
    return ''

  KeyPassphrase = property(
      GetKeyPassphrase, SetKeyPassphrase, None,
      'WLANConfiguration.{i}.PreSharedKey.{i}.KeyPassphrase')


class WEPKey(BASE98WIFI.WEPKey):
  """InternetGatewayDevice.WLANConfiguration.{i}.WEPKey.{i}."""

  WEPKey = tr.cwmptypes.TriggerString('')

  def __init__(self, parent):
    super(WEPKey, self).__init__()
    self.Unexport(['Alias'])
    self.parent = parent

  def Triggered(self):
    self.parent.Triggered()


class WlanConfigurationStats(netdev.NetdevStatsLinux26, BASE98WIFI.Stats):
  """tr98 InternetGatewayDevice.LANDevice.WLANConfiguration.Stats."""

  def __init__(self, ifname):
    netdev.NetdevStatsLinux26.__init__(self, ifname)
    BASE98WIFI.Stats.__init__(self)


def CollectSignalStrength(device):
  """Update the dictionary of signal strengths for each WlanConfiguration.

  Args:
    device: The Associated Device we need information for.
  """
  mac_addr = device.AssociatedDeviceMACAddress
  directory = STATIONS_DIR[0]
  last_sig_dict = dict(device.wlan.signals)
  new_sig_dict = dict(device.wlan.signals)
  # Check if file still exists if it is being deleted.
  if os.path.isfile(os.path.join(directory, mac_addr)):
    try:
      device_data = json.load(open(os.path.join(directory, mac_addr)))
    except ValueError:
      device_data = {'signal': {}}
    new_sig_dict[mac_addr] = device_data['signal']
  for mac_addr in new_sig_dict.keys():  # pylint: disable=g-builtin-op
    if mac_addr not in os.listdir(directory):
      del new_sig_dict[mac_addr]
  updated = False
  for mac_addr, signal in last_sig_dict.iteritems():
    try:
      if new_sig_dict[mac_addr] != signal:
        updated = True
    except KeyError:
      updated = True  # the device has been deleted, not in sig_dict anymore
  if len(last_sig_dict) != len(new_sig_dict) or updated:
    device.wlan.signals = new_sig_dict


class AssociatedDevice(CATA98WIFI.AssociatedDevice):
  """InternetGatewayDevice.LANDevice.WLANConfiguration.AssociatedDevice."""

  AssociatedDeviceAuthenticationState = tr.cwmptypes.ReadOnlyBool(True)
  AssociatedDeviceMACAddress = tr.cwmptypes.ReadOnlyMacAddr()
  # tr-098-1-6 defines LastDataTransmitRate as a string(4). Bizarre.
  LastDataTransmitRate = tr.cwmptypes.ReadOnlyString()
  X_CATAWAMPUS_ORG_Active = tr.cwmptypes.ReadOnlyBool(False)
  X_CATAWAMPUS_ORG_LastDataDownlinkRate = tr.cwmptypes.ReadOnlyUnsigned()
  X_CATAWAMPUS_ORG_LastDataUplinkRate = tr.cwmptypes.ReadOnlyUnsigned()
  X_CATAWAMPUS_ORG_SignalStrength = tr.cwmptypes.ReadOnlyInt()
  X_CATAWAMPUS_ORG_SignalStrengthAverage = tr.cwmptypes.ReadOnlyInt()
  X_CATAWAMPUS_ORG_StationInfo = tr.cwmptypes.FileBacked([''],
                                                         tr.cwmptypes.String(),
                                                         delete_if_empty=False)

  def __init__(self, device, filename, parent_wlan_configuration):
    """Constructor.

    Args:
      device: A dictionary containing information about the associated device,
          produced by WlanConfiguration._ParseBinWifi.
      filename: The path to the associated device information file, typically
          in /tmp/stations.
      parent_wlan_configuration: The WlanConfiguration object that this device
          is associated to.
    """
    super(AssociatedDevice, self).__init__()
    type(self).AssociatedDeviceMACAddress.Set(self, device.get('PhysAddr', ''))
    idle_since = device.get('inactive since', 0.0)
    # this operation is safe from clock jumps:
    # if the system clock jumps, the file will be rewritten with the new local
    # time, so the comparison with time.time() will still be valid
    idle_sec = time.time() - idle_since
    type(self).X_CATAWAMPUS_ORG_Active.Set(self, idle_sec < 120)

    bitrate = device.get('tx bitrate', 0.0)
    kbps = int(bitrate * 1000.0)
    type(self).X_CATAWAMPUS_ORG_LastDataUplinkRate.Set(self, kbps)

    bitrate = device.get('rx bitrate', 0.0)
    kbps = int(bitrate * 1000.0)
    mbps = int(bitrate)
    type(self).X_CATAWAMPUS_ORG_LastDataDownlinkRate.Set(self, kbps)
    type(self).LastDataTransmitRate.Set(self, mbps)

    dbm = device.get('signal', 0)
    type(self).X_CATAWAMPUS_ORG_SignalStrength.Set(self, dbm)
    dbm_avg = device.get('signal avg', 0)
    type(self).X_CATAWAMPUS_ORG_SignalStrengthAverage.Set(self, dbm_avg)

    self.Unexport(['AssociatedDeviceIPAddress', 'LastPMKId',
                   'LastRequestedUnicastCipher',
                   'LastRequestedMulticastCipher'])

    type(self).X_CATAWAMPUS_ORG_StationInfo.SetFileName(self, filename)
    self.wlan = parent_wlan_configuration
    tr.cwmptypes.AddNotifier(type(self), 'X_CATAWAMPUS_ORG_StationInfo',
                             CollectSignalStrength)

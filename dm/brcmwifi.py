#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-98/181 WLAN objects for Broadcom Wifi chipsets.

The platform code is expected to set the BSSID (which is really a MAC address).
The Wifi module should be populated with a MAC address. For example if it
appears as eth2, then "ifconfig eth2" will show the MAC address from the Wifi
card. The platform should execute:
  wl bssid xx:xx:xx:xx:xx:xx
To set the bssid to the desired MAC address, either the one from the wifi
card or your own.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import collections
import re
import subprocess
import tr.core
import tr.cwmpbool
import tr.tr098_v1_4
import netdev
import wifi

BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice
BASE98WIFI = BASE98IGD.LANDevice.WLANConfiguration
WL_EXE = '/usr/bin/wl'

# Supported Encryption Modes
EM_NONE = 0
EM_WEP = 1
EM_TKIP = 2
EM_AES = 4
EM_WSEC = 8  # Not enumerated in tr-98
EM_FIPS = 0x80  # Not enumerated in tr-98
EM_WAPI = 0x100  # Not enumerated in tr-98

# Beacon Types
BEACONS = frozenset(['None', 'Basic', 'WPA', '11i', 'BasicandWPA',
                     'Basicand11i', 'WPAand11i', 'BasicandWPAand11i'])


def IsInteger(value):
  try:
    int(value)
  except:  #pylint: disable-msg=W0702
    return False
  return True


def _SubprocessCall(cmd):
  subprocess.check_call(cmd)


def _SubprocessWithOutput(cmd):
  wl = subprocess.Popen(cmd, stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
  return out


def _GetWlCounters():
  out = _SubprocessWithOutput([WL_EXE, 'counters'])

  # match three different types of stat output:
  # rxuflo: 1 2 3 4 5 6
  # rxfilter 1
  # d11_txretrie
  st = re.compile('(\w+:?(?: \d+)*)')

  stats = st.findall(out)
  r1 = re.compile('(\w+): (.+)')
  r2 = re.compile('(\w+) (\d+)')
  r3 = re.compile('(\w+)')
  sdict = dict()
  for stat in stats:
    p1 = r1.match(stat)
    p2 = r2.match(stat)
    p3 = r3.match(stat)
    if p1 is not None:
      sdict[p1.group(1).lower()] = p1.group(2).split()
    elif p2 is not None:
      sdict[p2.group(1).lower()] = p2.group(2)
    elif p3 is not None:
      sdict[p3.group(1).lower()] = '0'
  return sdict


def _SetApMode():
  """Put device into AP mode."""
  _SubprocessCall([WL_EXE, 'ap', '1'])
  _SubprocessCall([WL_EXE, 'infra', '1'])


def _GetAssociatedDevices():
  """Return a list of MAC addresses of associated STAs."""
  out = _SubprocessWithOutput([WL_EXE, 'assoclist'])
  stamac_re = re.compile('((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})')
  stations = list()
  for line in out.splitlines():
    sta = stamac_re.search(line)
    if sta is not None:
      stations.append(sta.group(1))
  return stations


def _GetAssociatedDevice(mac):
  """Return information about as associated STA.

  Args:
    mac: MAC address of the requested STA as a string, xx:xx:xx:xx:xx:xx

  Returns:
    An AssociatedDevice namedtuple.
  """
  ad = collections.namedtuple(
      'AssociatedDevice', ('AssociatedDeviceMACAddress '
                           'AssociatedDeviceAuthenticationState '
                           'LastDataTransmitRate'))
  ad.AssociatedDeviceMACAddress = mac
  ad.AssociatedDeviceAuthenticationState = False
  ad.LastDataTransmitRate = '0'
  out = _SubprocessWithOutput([WL_EXE, 'sta_info', mac.upper()])
  tx_re = re.compile('rate of last tx pkt: (\d+) kbps')
  for line in out.splitlines():
    if line.find('AUTHENTICATED') >= 0:
      ad.AssociatedDeviceAuthenticationState = True
    tx_rate = tx_re.search(line)
    if tx_rate is not None:
      try:
        mbps = int(tx_rate.group(1)) / 1000
      except ValueError:
        mbps = 0
      ad.LastDataTransmitRate = str(mbps)
  return ad


def _GetAutoRateFallBackEnabled(arg):
  """Return WLANConfiguration.AutoRateFallBackEnabled as a boolean."""
  out = _SubprocessWithOutput([WL_EXE, 'interference'])
  mode_re = re.compile('\(mode (\d)\)')
  result = mode_re.search(out)
  mode = -1
  if result is not None:
    mode = int(result.group(1))
  return True if mode == 3 or mode == 4 else False


def _SetAutoRateFallBackEnabled(value):
  """Set WLANConfiguration.AutoRateFallBackEnabled, expects a boolean."""
  interference = 4 if value else 3
  _SubprocessCall([WL_EXE, 'interference', str(interference)])


def _ValidateAutoRateFallBackEnabled(value):
  return tr.cwmpbool.valid(value)


def _GetBasicDataTransmitRates(arg):
  out = _SubprocessWithOutput([WL_EXE, 'rateset'])
  basic_re = re.compile('([0123456789]+(?:\.[0123456789]+)?)\(b\)')
  return ','.join(basic_re.findall(out))


def _SetBasicDataTransmitRates(value):
  # TODO(dgentry) implement
  raise NotImplementedError()


def _ValidateBasicDataTransmitRates(value):
  # TODO(dgentry) implement
  raise NotImplementedError()


def _GetBSSID(arg):
  out = _SubprocessWithOutput([WL_EXE, 'bssid'])
  bssid_re = re.compile('((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})')
  for line in out.splitlines():
    bssid = bssid_re.match(line)
    if bssid is not None:
      return bssid.group(1)
  return '00:00:00:00:00:00'


def _SetBSSID(value):
  _SubprocessCall([WL_EXE, 'bssid', value])


def _ValidateBSSID(value):
  lower = value.lower()
  if lower == '00:00:00:00:00:00' or lower == 'ff:ff:ff:ff:ff:ff':
    return False
  bssid_re = re.compile('((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})')
  if bssid_re.search(value) is None:
    return False
  return True


def _GetBssStatus(arg):
  out = _SubprocessWithOutput([WL_EXE, 'bss'])
  lower = out.strip().lower()
  if lower == 'up':
    return 'Up'
  elif lower == 'down':
    return 'Disabled'
  else:
    return 'Error'


def _SetBssStatus(enable):
  status = 'up' if enable else 'down'
  _SubprocessCall([WL_EXE, 'bss', status])


def _ValidateBssStatus(value):
  return tr.cwmpbool.valid(value)


def _GetChannel(arg):
  out = _SubprocessWithOutput([WL_EXE, 'channel'])
  chan_re = re.compile('current mac channel(?:\s+)(\d+)')
  for line in out.splitlines():
    mr = chan_re.match(line)
    if mr is not None:
      return int(mr.group(1))
  return 0


def _SetChannel(value):
  _SubprocessCall([WL_EXE, 'channel', value])


def _ValidateChannel(value):
  if not IsInteger(value):
    return False
  iv = int(value)
  if iv in range(1, 14):
    return True  # 2.4 GHz. US allows 1-11, Japan allows 1-13.
  if iv in range(36, 144, 4):
    return True  # 5 GHz lower bands
  if iv in range(149, 169, 4):
    return True  # 5 GHz upper bands
  return False


def _ValidateEnable(value):
  return tr.cwmpbool.valid(value)


def _EM_StringToBitmap(enum):
  wsec = {'X_CATAWAMPUS-ORG_None': EM_NONE,
          'None': EM_NONE,
          'WEPEncryption': EM_WEP,
          'TKIPEncryption': EM_TKIP,
          'WEPandTKIPEncryption': EM_WEP | EM_TKIP,
          'AESEncryption': EM_AES,
          'WEPandAESEncryption': EM_WEP | EM_AES,
          'TKIPandAESEncryption': EM_TKIP | EM_AES,
          'WEPandTKIPandAESEncryption': EM_WEP | EM_TKIP | EM_AES}
  return wsec.get(enum, EM_NONE)


def _EM_BitmapToString(bitmap):
  bmap = {EM_NONE: 'X_CATAWAMPUS-ORG_None',
          EM_WEP: 'WEPEncryption',
          EM_TKIP: 'TKIPEncryption',
          EM_WEP | EM_TKIP: 'WEPandTKIPEncryption',
          EM_AES: 'AESEncryption',
          EM_WEP | EM_AES: 'WEPandAESEncryption',
          EM_TKIP | EM_AES: 'TKIPandAESEncryption',
          EM_WEP | EM_TKIP | EM_AES: 'WEPandTKIPandAESEncryption'}
  return bmap.get(bitmap)


def _GetEncryptionModes(arg):
  out = _SubprocessWithOutput([WL_EXE, 'wsec'])
  try:
    w = int(out.strip()) & 0x7
    return _EM_BitmapToString(w)
  except ValueError:
    return 'X_CATAWAMPUS-ORG_None'


def _SetEncryptionModes(value):
  _SubprocessCall([WL_EXE, 'wsec', str(value)])


def _ValidateEncryptionModes(value):
  ENCRYPTTYPES = frozenset(['X_CATAWAMPUS-ORG_None', 'None', 'WEPEncryption',
                            'TKIPEncryption', 'WEPandTKIPEncryption',
                            'AESEncryption', 'WEPandAESEncryption',
                            'TKIPandAESEncryption',
                            'WEPandTKIPandAESEncryption'])
  return True if value in ENCRYPTTYPES else False


def _GetOperationalDataTransmitRates(arg):
  out = _SubprocessWithOutput([WL_EXE, 'rateset'])
  oper_re = re.compile('([0123456789]+(?:\.[0123456789]+)?)')
  if out:
    line1 = out.splitlines()[0]
  else:
    line1 = ''
  return ','.join(oper_re.findall(line1))


def _SetOperationalDataTransmitRates(value):
  # TODO(dgentry) implement
  raise NotImplementedError()


def _ValidateOperationalDataTransmitRates(value):
  # TODO(dgentry) implement
  raise NotImplementedError()


def _GetPossibleChannels(arg):
  out = _SubprocessWithOutput([WL_EXE, 'channels'])
  if out:
    channels = [int(x) for x in out.split()]
    return wifi.ContiguousRanges(channels)
  else:
    return ''


def _GetRadioEnabled(arg):
  out = _SubprocessWithOutput([WL_EXE, 'radio'])
  # This may look backwards, but I assure you it is correct. If the
  # radio is off, 'wl radio' returns 0x0001.
  try:
    return False if int(out.strip(), 0) == 1 else True
  except ValueError:
    return False


def _SetRadioEnabled(value):
  radio = 'on' if value else 'off'
  _SubprocessCall([WL_EXE, 'radio', radio])


def _ValidateRadioEnabled(value):
  return tr.cwmpbool.valid(value)


def _GetRegulatoryDomain(arg):
  out = _SubprocessWithOutput([WL_EXE, 'country'])
  fields = out.split()
  if fields:
    return fields[0]
  else:
    return ''


def _SetRegulatoryDomain(value):
  _SubprocessCall([WL_EXE, 'country', value])


def _ValidateRegulatoryDomain(value):
  out = _SubprocessWithOutput([WL_EXE, 'country', 'list'])
  countries = set()
  for line in out.splitlines():
    fields = line.split(' ')
    if len(fields) and len(fields[0]) == 2:
      countries.add(fields[0])
  return True if value in countries else False


def _SetReset(do_reset):
  status = 'down' if do_reset else 'up'
  _SubprocessCall([WL_EXE, status])


def _GetSSID(arg):
  """Return current Wifi SSID."""
  out = _SubprocessWithOutput([WL_EXE, 'ssid'])
  ssid_re = re.compile('Current SSID: "(.*)"')
  for line in out.splitlines():
    ssid = ssid_re.match(line)
    if ssid is not None:
      return ssid.group(1)
  return ''


def _SetSSID(value):
  _SubprocessCall([WL_EXE, 'ssid', value])


def _ValidateSSID(value):
  if len(value) > 32:
    return False
  return True


def _GetSSIDAdvertisementEnabled(arg):
  out = _SubprocessWithOutput([WL_EXE, 'closed'])
  return True if out.strip() == '0' else False


def _SetSSIDAdvertisementEnabled(value):
  closed = '0' if value else '1'
  _SubprocessCall([WL_EXE, 'closed', closed])


def _ValidateSSIDAdvertisementEnabled(value):
  return tr.cwmpbool.valid(value)


def _GetTransmitPower(arg):
  out = _SubprocessWithOutput([WL_EXE, 'pwr_percent'])
  return out.strip()


def _SetTransmitPower(value):
  _SubprocessCall([WL_EXE, 'pwr_percent', value])


def _ValidateTransmitPower(value):
  if not IsInteger(value):
    return False
  percent = int(value)
  if percent < 0 or percent > 100:
    return False
  return True


def _GetTransmitPowerSupported(arg):
  # tr-98 describes this as a comma separated list, limited to string(64)
  # clearly it is expected to be a small number of discrete steps.
  # This chipset appears to have no such restriction. Hope a range is ok.
  return '1-100'


def _SetWepKey(index, key, mac=None):
  wl_cmd = [WL_EXE, 'addwep', str(index), key]
  if mac is not None:
    wl_cmd.append(mac)
  _SubprocessCall(wl_cmd)
  print(wl_cmd)


def _ClrWepKey(index):
  _SubprocessCall([WL_EXE, 'rmwep', str(index)])


def _SetWepKeyIndex(index):
  # We do not use check_call here because primary_key fails if no WEP
  # keys have been configured, but we keep the code simple to always set it.
  subprocess.call([WL_EXE, 'primary_key', str(index)])


def _SetWepStatus(enable):
  status = 'on' if enable else 'off'
  subprocess.call([WL_EXE, 'wepstatus', status])


class BrcmWifiWlanConfiguration(BASE98WIFI):
  """An implementation of tr98 WLANConfiguration for Broadcom Wifi chipsets."""

  def __init__(self, ifname):
    BASE98WIFI.__init__(self)
    self._ifname = ifname

    # Unimplemented, but not yet evaluated
    self.Unexport('AutoChannelEnable')
    self.Unexport('BeaconAdvertisementEnabled')
    self.Unexport('ChannelsInUse')
    self.Unexport('MaxBitRate')
    self.Unexport('PossibleDataTransmitRates')
    self.Unexport('TotalIntegrityFailures')
    self.Unexport('TotalPSKFailures')

    self.AssociatedDeviceList = tr.core.AutoDict(
        'AssociatedDeviceList', iteritems=self.IterAssociations,
        getitem=self.GetAssociationByIndex)

    self.PreSharedKeyList = {}
    for i in range(1, 5):
      # tr-98 spec deviation: spec says 10 PreSharedKeys objects,
      # BRCM only supports 4 keys.
      self.PreSharedKeyList[i] = wifi.PreSharedKey98()

    self.WEPKeyList = {}
    for i in range(1, 5):
      self.WEPKeyList[i] = wifi.WEPKey98()

    self.LocationDescription = ''

    # No RADIUS support, could be added later.
    self.Unexport('AuthenticationServiceMode')
    self.Unexport('BasicAuthenticationMode')
    self.Unexport('IEEE11iAuthenticationMode')
    self.Unexport('WPAAuthenticationMode')

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

    self._SetDefaults()

  def _SetDefaults(self):
    self.p_auto_rate_fallback_enabled = None
    self.p_basic_data_transmit_rates = None
    self.p_basic_encryption_modes = 'WEPEncryption'
    self.p_beacon_type = 'WPAand11i'
    self.p_bssid = None
    self.p_channel = None
    self.p_enable = False
    self.p_ieee11i_encryption_modes = 'X_CATAWAMPUS-ORG_None'
    self.p_operational_data_transmit_rates = None
    self.p_radio_enabled = True
    self.p_regulatory_domain = None
    self.p_ssid = None
    self.p_ssid_advertisement_enabled = None
    self.p_transmit_power = None
    self.p_wepkeyindex = 1
    self.p_wpa_encryption_modes = 'X_CATAWAMPUS-ORG_None'

  @property
  def Name(self):
    return self._ifname

  @property  # TODO(dgentry) need @sessioncache decorator.
  def Stats(self):
    return BrcmWlanConfigurationStats(self._ifname)

  @property
  def Standard(self):
    return 'n'

  @property
  def DeviceOperationMode(self):
    return 'InfrastructureAccessPoint'

  @property
  def UAPSDSupported(self):
    return False

  @property
  def WEPEncryptionLevel(self):
    return 'Disabled,40-bit,104-bit'

  @property
  def WMMSupported(self):
    return False

  @property
  def TotalAssociations(self):
    return len(self.AssociatedDeviceList)

  def SetAutoRateFallBackEnabled(self, value):
    self.p_auto_rate_fallback_enabled = tr.cwmpbool.parse(value)
    self._ConfigureBrcmWifi()

  AutoRateFallBackEnabled = property(
      _GetAutoRateFallBackEnabled, SetAutoRateFallBackEnabled, None,
      'WLANConfiguration.AutoRateFallBackEnabled')

  def SetBasicDataTransmitRates(self, value):
    self.p_basic_data_transmit_rates = value
    self._ConfigureBrcmWifi()

  BasicDataTransmitRates = property(
      _GetBasicDataTransmitRates, SetBasicDataTransmitRates, None,
      'WLANConfiguration.BasicDataTransmitRates')

  def GetBasicEncryptionModes(self):
    return self.p_basic_encryption_modes

  def SetBasicEncryptionModes(self, value):
    self.p_basic_encryption_modes = value

  def ValidateBasicEncryptionModes(self, value):
    CRYPTO = ['None', 'WEPEncryption']
    return True if value in CRYPTO else False

  BasicEncryptionModes = property(GetBasicEncryptionModes,
                                  SetBasicEncryptionModes, None,
                                  'WLANConfiguration.BasicEncryptionModes')

  def GetBeaconType(self):
    return self.p_beacon_type

  def SetBeaconType(self, value):
    self.p_beacon_type = value
    self._ConfigureBrcmWifi()

  def ValidateBeaconType(self, value):
    return True if value in BEACONS else False

  BeaconType = property(GetBeaconType, SetBeaconType, None,
                        'WLANConfiguration.BeaconType')

  def SetBSSID(self, value):
    self.p_bssid = value
    self._ConfigureBrcmWifi()

  BSSID = property(_GetBSSID, SetBSSID, None, 'WLANConfiguration.BSSID')

  def SetChannel(self, value):
    self.p_channel = value
    self._ConfigureBrcmWifi()

  Channel = property(_GetChannel, SetChannel, None, 'WLANConfiguration.Channel')

  def GetEnable(self):
    return self.p_enable

  def SetEnable(self, value):
    self.p_enable = tr.cwmpbool.parse(value)
    self._ConfigureBrcmWifi()

  def ValidateEnable(self, value):
    return _ValidateEnable(value)

  Enable = property(GetEnable, SetEnable, None, 'WLANConfiguration.Enable')

  def SetIEEE11iEncryptionModes(self, value):
    self.p_ieee11i_encryption_modes = value
    self._ConfigureBrcmWifi()

  IEEE11iEncryptionModes = property(
      _GetEncryptionModes, SetIEEE11iEncryptionModes, None,
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

  def SetOperationalDataTransmitRates(self, value):
    self.p_operational_data_transmit_rates = value
    self._ConfigureBrcmWifi()

  OperationalDataTransmitRates = property(
      _GetOperationalDataTransmitRates, SetOperationalDataTransmitRates, None,
      'WLANConfiguration.OperationalDataTransmitRates')

  PossibleChannels = property(_GetPossibleChannels, None, None,
                              'WLANConfiguration.PossibleChannels')

  def SetRadioEnabled(self, value):
    self.p_radio_enabled = tr.cwmpbool.parse(value)
    self._ConfigureBrcmWifi()

  RadioEnabled = property(
      _GetRadioEnabled, SetRadioEnabled, None,
      'WLANConfiguration.RadioEnabled')

  def SetRegulatoryDomain(self, value):
    self.p_regulatory_domain = value
    self._ConfigureBrcmWifi()

  RegulatoryDomain = property(
      _GetRegulatoryDomain, SetRegulatoryDomain, None,
      'WLANConfiguration.RegulatoryDomain')

  def SetSSID(self, value):
    self.p_ssid = value
    self._ConfigureBrcmWifi()

  SSID = property(_GetSSID, SetSSID, None, 'WLANConfiguration.SSID')

  def SetSSIDAdvertisementEnabled(self, value):
    self.p_ssid_advertisement_enabled = tr.cwmpbool.parse(value)
    self._ConfigureBrcmWifi()

  SSIDAdvertisementEnabled = property(
      _GetSSIDAdvertisementEnabled, SetSSIDAdvertisementEnabled, None,
      'WLANConfiguration.SSIDAdvertisementEnabled')

  Status = property(_GetBssStatus, None, None, 'WLANConfiguration.Status')

  def SetTransmitPower(self, value):
    self.p_transmit_power = value
    self._ConfigureBrcmWifi()

  TransmitPower = property(_GetTransmitPower, SetTransmitPower, None,
                           'WLANConfiguration.TransmitPower')

  TransmitPowerSupported = property(
      _GetTransmitPowerSupported, None, None,
      'WLANConfiguration.TransmitPowerSupported')

  def GetWEPKeyIndex(self):
    return self.p_wepkeyindex

  def SetWEPKeyIndex(self, value):
    self.p_wepkeyindex = int(value)

  WEPKeyIndex = property(GetWEPKeyIndex, SetWEPKeyIndex, None,
                         'WLANConfiguration.WEPKeyIndex')

  def SetWPAEncryptionModes(self, value):
    self.p_wpa_encryption_modes = value
    self._ConfigureBrcmWifi()

  WPAEncryptionModes = property(
      _GetEncryptionModes, SetWPAEncryptionModes, None,
      'WLANConfiguration.WPAEncryptionModes')

  # TODO(dgentry) we shouldn't call this from every Set*. There should
  # be a callback once the entire SetParameterValues has been processed.
  def _ConfigureBrcmWifi(self):
    """Issue commands to the wifi device to configure it.

    The Wifi driver is somewhat picky about the order of the commands.
    For example, some settings can only be changed while the radio is on.
    """

    _SetReset(True)
    if not self.p_enable:
      return
    _SetRadioEnabled(False)
    _SetBssStatus(False)
    if self.p_radio_enabled is False:
      return

    _SetRadioEnabled(True)
    _SetReset(False)
    _SetApMode()
    if self.p_auto_rate_fallback_enabled is not None:
      _SetAutoRateFallBackEnabled(self.p_auto_rate_fallback_enabled)
    if self.p_basic_data_transmit_rates is not None:
      _SetBasicDataTransmitRates(self.p_basic_data_transmit_rates)
    if self.p_bssid is not None:
      _SetBSSID(self.p_bssid)
    if self.p_channel is not None:
      _SetChannel(self.p_channel)
    if self.p_operational_data_transmit_rates is not None:
      _SetOperationalDataTransmitRates(
          self.p_operational_data_transmit_rates)
    if self.p_regulatory_domain is not None:
      _SetRegulatoryDomain(self.p_regulatory_domain)
    if self.p_ssid is not None:
      _SetSSID(self.p_ssid)
    if self.p_ssid_advertisement_enabled is not None:
      _SetSSIDAdvertisementEnabled(self.p_ssid_advertisement_enabled)
    if self.p_transmit_power is not None:
      _SetTransmitPower(self.p_transmit_power)

    if self.p_beacon_type.find('11i') >= 0:
      crypto = _EM_StringToBitmap(self.p_ieee11i_encryption_modes)
    elif self.p_beacon_type.find('WPA') >= 0:
      crypto = _EM_StringToBitmap(self.p_wpa_encryption_modes)
    elif self.p_beacon_type.find('Basic') >= 0:
      crypto = _EM_StringToBitmap(self.p_basic_encryption_modes)
    else:
      crypto = EM_NONE
    _SetEncryptionModes(crypto)

    if self.p_beacon_type.find('Basic') >= 0:
      _SetWepStatus(True)
    else:
      _SetWepStatus(False)

    for idx, wep in self.WEPKeyList.items():
      key = wep.WEPKey
      if key is None:
        _ClrWepKey(idx-1)
      else:
        _SetWepKey(idx-1, key)
    _SetWepKeyIndex(self.p_wepkeyindex)
    if self.p_ssid:
      # bss can only be turned on if SSID is set.
      _SetBssStatus(True)

  def GetTotalBytesReceived(self):
    counters = _GetWlCounters()  # TODO(dgentry) cache for lifetime of session
    return int(counters.get('rxbyte', 0))
  TotalBytesReceived = property(
      GetTotalBytesReceived, None, None,
      'WLANConfiguration.TotalBytesReceived')

  def GetTotalBytesSent(self):
    counters = _GetWlCounters()  # TODO(dgentry) cache for lifetime of session
    return int(counters.get('txbyte', 0))
  TotalBytesSent = property(GetTotalBytesSent, None, None,
                            'WLANConfiguration.TotalBytesSent')

  def GetTotalPacketsReceived(self):
    counters = _GetWlCounters()  # TODO(dgentry) cache for lifetime of session
    return int(counters.get('rxframe', 0))
  TotalPacketsReceived = property(GetTotalPacketsReceived, None, None,
                                  'WLANConfiguration.TotalPacketsReceived')

  def GetTotalPacketsSent(self):
    counters = _GetWlCounters()  # TODO(dgentry) cache for lifetime of session
    return int(counters.get('txframe', 0))
  TotalPacketsSent = property(GetTotalPacketsSent, None, None,
                              'WLANConfiguration.TotalPacketsSent')

  def GetAssociation(self, mac):
    """Get an AssociatedDevice object for the given STA."""
    ad = BrcmWlanAssociatedDevice(_GetAssociatedDevice(mac))
    if ad:
      ad.ValidateExports()
    return ad

  def IterAssociations(self):
    """Retrieves a list of all associated STAs."""
    stations = _GetAssociatedDevices()
    for idx, mac in enumerate(stations):
      yield idx, self.GetAssociation(mac)

  def GetAssociationByIndex(self, index):
    stations = _GetAssociatedDevices()
    return self.GetAssociation(stations[index])


class BrcmWlanConfigurationStats(BASE98WIFI.Stats):
  """tr98 InternetGatewayDevice.LANDevice.WLANConfiguration.Stats."""

  def __init__(self, ifname):
    BASE98WIFI.Stats.__init__(self)
    self._netdev = netdev.NetdevStatsLinux26(ifname)

  def __getattr__(self, name):
    if hasattr(self._netdev, name):
      return getattr(self._netdev, name)
    else:
      raise AttributeError


class BrcmWlanAssociatedDevice(BASE98WIFI.AssociatedDevice):
  """Implementation of tr98 AssociatedDevice for Broadcom Wifi chipsets."""

  def __init__(self, device):
    BASE98WIFI.AssociatedDevice.__init__(self)
    self._device = device
    self.Unexport('AssociatedDeviceIPAddress')
    self.Unexport('LastPMKId')
    self.Unexport('LastRequestedUnicastCipher')
    self.Unexport('LastRequestedMulticastCipher')

  def __getattr__(self, name):
    if hasattr(self._device, name):
      return getattr(self._device, name)
    else:
      raise AttributeError


def main():
  pass

if __name__ == '__main__':
  main()

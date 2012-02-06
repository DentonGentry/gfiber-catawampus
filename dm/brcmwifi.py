#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-98/181 WLAN objects for Broadcom Wifi chipsets."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import collections
import re
import subprocess
import netdev
import tr.core
import tr.cwmpbool
import tr.tr098_v1_2 as tr98

BASE98IGD = tr98.InternetGatewayDevice_v1_4.InternetGatewayDevice
BASE98WIFI = BASE98IGD.LANDevice.WLANConfiguration
WL_EXE = '/usr/bin/wl'


def IsInteger(value):
  try:
    int(value)
  except:  #pylint: disable-msg=W0702
    return False
  return True


def _GetWlCounters():
  wl = subprocess.Popen([WL_EXE, 'counters'], stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)

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


def _OutputContiguousRanges(seq):
  """Given an integer sequence, return contiguous ranges.

  Args:
    seq: a sequence of integers, like [1,2,3,4,5]

  Returns:
    A string of the collapsed ranges.
    Given [1,2,3,4,5] as input, will return '1-5'
  """
  in_range = False
  prev = seq[0]
  output = list(str(seq[0]))
  for item in seq[1:]:
    if item == prev + 1:
      if not in_range:
        in_range = True
        output.append('-')
    else:
      if in_range:
        output.append(str(prev))
      output.append(',' + str(item))
      in_range = False
    prev = item
  if in_range:
    output.append(str(prev))
  return ''.join(output)


def _GetAssociatedDevices():
  """Return a list of MAC addresses of associated STAs."""
  wl = subprocess.Popen([WL_EXE, 'assoclist'], stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
  stamac_re = re.compile('((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})')
  stations = list()
  for line in out.splitlines():
    sta = stamac_re.search(line)
    if sta is not None:
      stations.append(sta.group(1))
  return stations


def _GetAssociatedDevice(mac):
  ad = collections.namedtuple(
      'AssociatedDevice', ('AssociatedDeviceMACAddress '
                           'AssociatedDeviceAuthenticationState '
                           'LastDataTransmitRate'))
  ad.AssociatedDeviceMACAddress = mac
  ad.AssociatedDeviceAuthenticationState = False
  ad.LastDataTransmitRate = '0'
  wl = subprocess.Popen([WL_EXE, 'sta_info', mac.upper()],
                        stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
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
  wl = subprocess.Popen([WL_EXE, 'interference'], stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
  mode_re = re.compile('\(mode (\d)\)')
  result = mode_re.search(out)
  mode = -1
  if result is not None:
    mode = int(result.group(1))
  return True if mode == 3 or mode == 4 else False


def _SetAutoRateFallBackEnabled(arg, value):
  interference = 4 if tr.cwmpbool.parse(value) else 3
  subprocess.check_call([WL_EXE, 'interference', str(interference)])


def _ValidateAutoRateFallBackEnabled(value):
  return tr.cwmpbool.valid(value)


def _GetBasicDataTransmitRates(arg):
  wl = subprocess.Popen([WL_EXE, 'rateset'], stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
  basic_re = re.compile('([0123456789]+(?:\.[0123456789]+)?)\(b\)')
  return ','.join(basic_re.findall(out))


def _SetBasicDataTransmitRates(arg, value):
  # TODO(dgentry) implement
  raise NotImplementedError()


def _ValidateBasicDataTransmitRates(value):
  # TODO(dgentry) implement
  raise NotImplementedError()


def _GetBSSID(arg):
  wl = subprocess.Popen([WL_EXE, 'bssid'], stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
  bssid_re = re.compile('((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})')
  for line in out.splitlines():
    bssid = bssid_re.match(line)
    if bssid is not None:
      return bssid.group(1)
  return '00:00:00:00:00:00'


def _SetBSSID(arg, value):
  subprocess.check_call([WL_EXE, 'bssid', value])


def _ValidateBSSID(value):
  lower = value.lower()
  if lower == '00:00:00:00:00:00' or lower == 'ff:ff:ff:ff:ff:ff':
    return False
  bssid_re = re.compile('((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})')
  if bssid_re.search(value) is None:
    return False
  return True


def _GetChannel(arg):
  wl = subprocess.Popen([WL_EXE, 'channel'], stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
  chan_re = re.compile('current mac channel(?:\s+)(\d+)')
  for line in out.splitlines():
    mr = chan_re.match(line)
    if mr is not None:
      return int(mr.group(1))
  return 0


def _SetChannel(arg, value):
  subprocess.check_call([WL_EXE, 'channel', value])


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


def _GetOperationalDataTransmitRates(arg):
  wl = subprocess.Popen([WL_EXE, 'rateset'], stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
  oper_re = re.compile('([0123456789]+(?:\.[0123456789]+)?)')
  if out:
    line1 = out.splitlines()[0]
  else:
    line1 = ''
  return ','.join(oper_re.findall(line1))


def _SetOperationalDataTransmitRates(arg, value):
  # TODO(dgentry) implement
  raise NotImplementedError()


def _ValidateOperationalDataTransmitRates(value):
  # TODO(dgentry) implement
  raise NotImplementedError()


def _GetPossibleChannels(arg):
  wl = subprocess.Popen([WL_EXE, 'channels'], stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
  if out:
    channels = [int(x) for x in out.split()]
    return _OutputContiguousRanges(channels)
  else:
    return ''


def _GetRadioEnabled(arg):
  wl = subprocess.Popen([WL_EXE, 'radio'], stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
  # This may look backwards, but I assure you it is correct. If the
  # radio is off, 'wl radio' returns 0x0001.
  try:
    return False if int(out.strip(), 0) == 1 else True
  except ValueError:
    return False


def _SetRadioEnabled(arg, value):
  radio = 'on' if tr.cwmpbool.parse(value) else 'off'
  subprocess.check_call([WL_EXE, 'radio', radio])


def _ValidateRadioEnabled(value):
  return tr.cwmpbool.valid(value)


def _GetRegulatoryDomain(arg):
  wl = subprocess.Popen([WL_EXE, 'country'], stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
  fields = out.split()
  if fields:
    return fields[0]
  else:
    return ''


def _SetRegulatoryDomain(arg, value):
  subprocess.check_call([WL_EXE, 'country', value])


def _ValidateRegulatoryDomain(value):
  wl = subprocess.Popen([WL_EXE, 'country', 'list'], stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
  countries = set()
  for line in out.splitlines():
    fields = line.split(' ')
    if len(fields) and len(fields[0]) == 2:
      countries.add(fields[0])
  return True if value in countries else False


def _GetSSID(arg):
  """Return current Wifi SSID."""
  wl = subprocess.Popen([WL_EXE, 'ssid'], stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
  ssid_re = re.compile('Current SSID: "(.*)"')
  for line in out.splitlines():
    ssid = ssid_re.match(line)
    if ssid is not None:
      return ssid.group(1)
  return ''


def _SetSSID(arg, value):
  subprocess.check_call([WL_EXE, 'ssid', value])


def _ValidateSSID(value):
  invalid = set(['?', '"', '$', '\\', '[', ']', '+'])
  for i in invalid:
    if i in value:
      return False
  if value[0] == '!' or value[0] == '#' or value[0] == ';':
    return False
  return True


def _GetSSIDAdvertisementEnabled(arg):
  wl = subprocess.Popen([WL_EXE, 'closed'], stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
  return True if out.strip() == '0' else False


def _SetSSIDAdvertisementEnabled(arg, value):
  closed = '0' if tr.cwmpbool.parse(value) else '1'
  subprocess.check_call([WL_EXE, 'closed', closed])


def _ValidateSSIDAdvertisementEnabled(value):
  return tr.cwmpbool.valid(value)


def _GetStatus(arg):
  wl = subprocess.Popen([WL_EXE, 'bss'], stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
  lower = out.strip().lower()
  if lower == 'up':
    return 'Up'
  elif lower == 'down':
    return 'Disabled'
  else:
    return 'Error'


def _SetStatus(arg, enable):
  status = 'up' if enable else 'down'
  subprocess.check_call([WL_EXE, 'status', status])


def _ValidateStatus(value):
  return tr.cwmpbool.valid(value)


def _GetTransmitPower(arg):
  wl = subprocess.Popen([WL_EXE, 'pwr_percent'], stdout=subprocess.PIPE)
  out, _ = wl.communicate(None)
  return out.strip()


def _SetTransmitPower(arg, value):
  subprocess.check_call([WL_EXE, 'pwr_percent', value])


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


class BrcmWifiWlanConfiguration(BASE98WIFI):
  """An implementation of tr98 WLANConfiguration for Broadcom Wifi chipsets."""

  def __init__(self, ifname):
    BASE98WIFI.__init__(self)
    self._ifname = ifname
    self._enabled = False
    self.AuthenticationServiceMode = tr.core.TODO()
    self.AutoChannelEnable = tr.core.TODO()
    self.BasicAuthenticationMode = tr.core.TODO()
    self.BasicEncryptionModes = tr.core.TODO()
    self.BeaconAdvertisementEnabled = tr.core.TODO()
    self.BeaconType = tr.core.TODO()
    self.ChannelsInUse = tr.core.TODO()
    self.IEEE11iAuthenticationMode = tr.core.TODO()
    self.IEEE11iEncryptionModes = tr.core.TODO()
    self.KeyPassphrase = tr.core.TODO()
    self.LocationDescription = ''
    self.MaxBitRate = tr.core.TODO()
    self.PreSharedKeyList = {}
    self.PossibleDataTransmitRates = tr.core.TODO()
    self.TotalIntegrityFailures = tr.core.TODO()
    self.TotalPSKFailures = tr.core.TODO()
    self.WEPEncryptionLevel = tr.core.TODO()
    self.WEPKeyList = {}
    self.WEPKeyIndex = tr.core.TODO()
    self.WPAAuthenticationMode = tr.core.TODO()
    self.WPAEncryptionModes = tr.core.TODO()

    self.AssociatedDeviceList = tr.core.AutoDict(
        'AssociatedDeviceList', iteritems=self.IterAssociations,
        getitem=self.GetAssociationByIndex)

    # Local settings, currently unimplemented. Will require more
    # coordination with the underlying platform support.
    self.Unexport('InsecureOOBAccessEnabled')

    # MAC Access controls, currently unimplemented but could be supported.
    self.Unexport('MACAddressControlEnabled')

    # Wifi Protected Setup, currently unimplemented and not recommended,
    # but could be supported if really desired.
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
  def WMMSupported(self):
    return False

  @property
  def TotalAssociations(self):
    return len(self.AssociatedDeviceList)

  def GetEnable(self):
    return self._enabled

  def SetEnable(self, value):
    self._enabled = tr.cwmpbool.parse(value)
    _SetStatus(None, self._enabled)

  def ValidateEnable(self, value):
    return _ValidateStatus(value)

  Enable = property(GetEnable, SetEnable, None, 'WLANConfiguration.Enable')

  AutoRateFallBackEnabled = property(
      _GetAutoRateFallBackEnabled, _SetAutoRateFallBackEnabled, None,
      'WLANConfiguration.AutoRateFallBackEnabled')
  BasicDataTransmitRates = property(
      _GetBasicDataTransmitRates, _SetBasicDataTransmitRates, None,
      'WLANConfiguration.BasicDataTransmitRates')
  BSSID = property(_GetBSSID, _SetBSSID, None, 'WLANConfiguration.BSSID')
  Channel = property(
      _GetChannel, _SetChannel, None,
      'WLANConfiguration.Channel')
  OperationalDataTransmitRates = property(
      _GetOperationalDataTransmitRates, _SetOperationalDataTransmitRates, None,
      'WLANConfiguration.OperationalDataTransmitRates')
  PossibleChannels = property(
      _GetPossibleChannels, None, None,
      'WLANConfiguration.PossibleChannels')
  RadioEnabled = property(
      _GetRadioEnabled, _SetRadioEnabled, None,
      'WLANConfiguration.RadioEnabled')
  RegulatoryDomain = property(
      _GetRegulatoryDomain, _SetRegulatoryDomain, None,
      'WLANConfiguration.RegulatoryDomain')
  SSID = property(_GetSSID, _SetSSID, None, 'WLANConfiguration.SSID')
  SSIDAdvertisementEnabled = property(
      _GetSSIDAdvertisementEnabled, _SetSSIDAdvertisementEnabled, None,
      'WLANConfiguration.SSIDAdvertisementEnabled')
  Status = property(
      _GetStatus, None, None,
      'WLANConfiguration.Status')
  TransmitPower = property(
      _GetTransmitPower, _SetTransmitPower, None,
      'WLANConfiguration.TransmitPower')
  TransmitPowerSupported = property(
      _GetTransmitPowerSupported, None, None,
      'WLANConfiguration.TransmitPowerSupported')

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

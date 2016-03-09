#!/usr/bin/python
# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Implementation of TR-69 objects for Glaukus Manager.

Documentation on the JSON fields that Glaukus Manager sends can be found at:
http://go/glaukus-manager-json-mappings
"""

__author__ = 'cgibson@google.com (Chris Gibson)'

import json
import os
import google3
import tr.cwmptypes
import tr.x_catawampus_tr181_2_0

BASE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
CATA181GLAUKUS = BASE.Device.X_CATAWAMPUS_ORG.Glaukus

# These can be overridden by unit tests.
MODEM_JSON_FILE = '/tmp/glaukus/modem.json'
RADIO_JSON_FILE = '/tmp/glaukus/radio.json'


class JsonReader(object):
  """Converts JSON files to Python objects."""

  def __init__(self):
    self._json_data = {}

  def LoadJsonFromFile(self, path, json_keys=None):
    """Deserializes a JSON file to a Python object.

    Args:
      path: The path to the JSON file to be converted.
      json_keys: A string of dot-delimited keys used to point to the JSON data
                 in the dict.

    Raises:
      OSError/IOError: If the JSON data file could not be loaded.
      ValueError: If the JSON data loaded from the file does not contain the
                  requested key, a ValueError is raised.
    """
    self._json_data = {}
    if not os.path.exists(path):
      # It is a valid state that there might not be a JSON data file yet,
      # so just return without printing an error.
      return

    try:
      with open(path) as f:
        self._json_data = json.load(f)
      if json_keys:
        for key in json_keys.split('.'):
          if not self._json_data.has_key(key):
            raise ValueError('JSON data does not have key: %s' % key)
          self._json_data = self._json_data[key]
    except (IOError, OSError) as ex:
      print 'Failed to load %s: %s' % (path, ex)
      return
    except ValueError as ex:
      # Limit output length or logos will clip the line.
      print 'Failed to decode JSON! path:%s, content:%s, %s' % (
          path, str(self._json_data)[0:70], ex)
      return

  def GetStat(self, value, default=0):
    """Get a statistic that was loaded from the JSON data file.

    Args:
      value: A dot-delimited value string used as a path to point to the JSON
            data in the dict.
      default: A default value returned if there is a problem with the lookup.

    Raises:
      ValueError: If the JSON data loaded from the file does not contain the
                  requested attribute.

    Returns:
      The requested JSON statistic or the supplied default value if not present.
      Otherwise, if no default value was specified and the value is not found,
      return 0 as this satisifies almost all cases safely.
    """
    if not value:
      return default

    if '.' not in value:
      return self._json_data.get(value, default)

    tmp_json_data = self._json_data
    keys = value.split('.')
    for key in keys:
      if not tmp_json_data.has_key(key):
        print 'JSON data does not have key: %s (%s)' % (key, value)
        return default
      tmp_json_data = tmp_json_data[key]
    return tmp_json_data


class Glaukus(CATA181GLAUKUS):
  """Device.X_CATAWAMPUS_ORG.Glaukus."""

  def __init__(self):
    super(Glaukus, self).__init__()
    self.json_reader = JsonReader()

  @property
  def Modem(self):
    return Modem(self.json_reader)

  @property
  def Radio(self):
    return Radio(self.json_reader)


class Modem(CATA181GLAUKUS.Modem):
  """Catawampus implementation of Glaukus Manager modem statistics."""

  StatusCode = tr.cwmptypes.ReadOnlyInt()
  StatusStr = tr.cwmptypes.ReadOnlyString()
  ModemFirmware = tr.cwmptypes.ReadOnlyString()
  ModemProfile = tr.cwmptypes.ReadOnlyString()

  def __init__(self, json_reader):
    super(Modem, self).__init__()
    self.json_reader = json_reader
    json_reader.LoadJsonFromFile(MODEM_JSON_FILE)
    type(self).ModemFirmware.Set(self, json_reader.GetStat('firmware'))
    type(self).ModemProfile.Set(self, json_reader.GetStat('profile'))
    type(self).StatusCode.Set(self, json_reader.GetStat('network.status'))
    type(self).StatusStr.Set(self, json_reader.GetStat('network.statusStr'))

  @property
  def RxCounters(self):
    return ModemRxCounters(self.json_reader)

  @property
  def TxCounters(self):
    return ModemTxCounters(self.json_reader)

  @property
  def Status(self):
    return ModemStatus(self.json_reader)

  @property
  def Transmitter(self):
    return ModemTransmitter(self.json_reader)

  @property
  def ModemVersion(self):
    return ModemVersion(self.json_reader)


class ModemVersion(CATA181GLAUKUS.Modem.ModemVersion):
  """Glaukus Manager modem version."""

  Build = tr.cwmptypes.ReadOnlyInt()
  ChipType = tr.cwmptypes.ReadOnlyString()
  Major = tr.cwmptypes.ReadOnlyInt()
  Minor = tr.cwmptypes.ReadOnlyInt()

  def __init__(self, json_reader):
    super(ModemVersion, self).__init__()
    json_reader.LoadJsonFromFile(MODEM_JSON_FILE, 'version')
    type(self).Build.Set(self, json_reader.GetStat('build'))
    type(self).ChipType.Set(self, json_reader.GetStat('chipType'))
    type(self).Major.Set(self, json_reader.GetStat('major'))
    type(self).Minor.Set(self, json_reader.GetStat('minor'))


class ModemTransmitter(CATA181GLAUKUS.Modem.Transmitter):
  """Glaukus Manager modem transmitter status."""

  DcLeakageI = tr.cwmptypes.ReadOnlyInt()
  DcLeakageQ = tr.cwmptypes.ReadOnlyInt()
  Mode = tr.cwmptypes.ReadOnlyInt()
  ModeStr = tr.cwmptypes.ReadOnlyString()
  SweepTime = tr.cwmptypes.ReadOnlyInt()
  ToneFreq = tr.cwmptypes.ReadOnlyInt()
  ToneSecFreq = tr.cwmptypes.ReadOnlyInt()

  def __init__(self, json_reader):
    super(ModemTransmitter, self).__init__()
    json_reader.LoadJsonFromFile(MODEM_JSON_FILE, 'transmitter')
    type(self).DcLeakageI.Set(self, json_reader.GetStat('dcLeakageI'))
    type(self).DcLeakageQ.Set(self, json_reader.GetStat('dcLeakageQ'))
    type(self).Mode.Set(self, json_reader.GetStat('mode'))
    type(self).ModeStr.Set(self, json_reader.GetStat('modeStr'))
    type(self).SweepTime.Set(self, json_reader.GetStat('sweepTime'))
    type(self).ToneFreq.Set(self, json_reader.GetStat('toneFreq'))
    type(self).ToneSecFreq.Set(self, json_reader.GetStat('toneSecFreq'))


class ModemRxCounters(CATA181GLAUKUS.Modem.RxCounters):
  """Glaukus Manager modem RX counters."""

  Broadcast = tr.cwmptypes.ReadOnlyInt()
  Bytes = tr.cwmptypes.ReadOnlyInt()
  CrcErrors = tr.cwmptypes.ReadOnlyInt()
  Frames = tr.cwmptypes.ReadOnlyInt()
  Frames1024_1518 = tr.cwmptypes.ReadOnlyInt()
  Frames128_255 = tr.cwmptypes.ReadOnlyInt()
  Frames256_511 = tr.cwmptypes.ReadOnlyInt()
  Frames512_1023 = tr.cwmptypes.ReadOnlyInt()
  Frames64 = tr.cwmptypes.ReadOnlyInt()
  Frames65_127 = tr.cwmptypes.ReadOnlyInt()
  FramesJumbo = tr.cwmptypes.ReadOnlyInt()
  FramesUndersized = tr.cwmptypes.ReadOnlyInt()
  Multicast = tr.cwmptypes.ReadOnlyInt()
  Unicast = tr.cwmptypes.ReadOnlyInt()

  def __init__(self, json_reader):
    super(ModemRxCounters, self).__init__()
    json_reader.LoadJsonFromFile(MODEM_JSON_FILE, 'network.rxCounters')
    type(self).Broadcast.Set(self, json_reader.GetStat('broadcast'))
    type(self).Bytes.Set(self, json_reader.GetStat('bytes'))
    type(self).CrcErrors.Set(self, json_reader.GetStat('crcErrors'))
    type(self).Frames.Set(self, json_reader.GetStat('frames'))
    type(self).Frames1024_1518.Set(self, json_reader.GetStat('frames1024_1518'))
    type(self).Frames128_255.Set(self, json_reader.GetStat('frames128_255'))
    type(self).Frames256_511.Set(self, json_reader.GetStat('frames256_511'))
    type(self).Frames512_1023.Set(self, json_reader.GetStat('frames512_1023'))
    type(self).Frames64.Set(self, json_reader.GetStat('frames64'))
    type(self).Frames65_127.Set(self, json_reader.GetStat('frames65_127'))
    type(self).FramesJumbo.Set(self, json_reader.GetStat('framesJumbo'))
    type(self).FramesUndersized.Set(self, json_reader.GetStat(
        'framesUndersized'))
    type(self).Multicast.Set(self, json_reader.GetStat('multicast'))
    type(self).Unicast.Set(self, json_reader.GetStat('unicast'))


class ModemTxCounters(CATA181GLAUKUS.Modem.TxCounters):
  """Glaukus Manager modem TX counters."""

  Broadcast = tr.cwmptypes.ReadOnlyInt()
  Bytes = tr.cwmptypes.ReadOnlyInt()
  CrcErrors = tr.cwmptypes.ReadOnlyInt()
  Frames = tr.cwmptypes.ReadOnlyInt()
  Frames1024_1518 = tr.cwmptypes.ReadOnlyInt()
  Frames128_255 = tr.cwmptypes.ReadOnlyInt()
  Frames256_511 = tr.cwmptypes.ReadOnlyInt()
  Frames512_1023 = tr.cwmptypes.ReadOnlyInt()
  Frames64 = tr.cwmptypes.ReadOnlyInt()
  Frames65_127 = tr.cwmptypes.ReadOnlyInt()
  FramesJumbo = tr.cwmptypes.ReadOnlyInt()
  FramesUndersized = tr.cwmptypes.ReadOnlyInt()
  Multicast = tr.cwmptypes.ReadOnlyInt()
  Unicast = tr.cwmptypes.ReadOnlyInt()

  def __init__(self, json_reader):
    super(ModemTxCounters, self).__init__()
    json_reader.LoadJsonFromFile(MODEM_JSON_FILE, 'network.txCounters')
    type(self).Broadcast.Set(self, json_reader.GetStat('broadcast'))
    type(self).Bytes.Set(self, json_reader.GetStat('bytes'))
    type(self).CrcErrors.Set(self, json_reader.GetStat('crcErrors'))
    type(self).Frames.Set(self, json_reader.GetStat('frames'))
    type(self).Frames1024_1518.Set(self, json_reader.GetStat('frames1024_1518'))
    type(self).Frames128_255.Set(self, json_reader.GetStat('frames128_255'))
    type(self).Frames256_511.Set(self, json_reader.GetStat('frames256_511'))
    type(self).Frames512_1023.Set(self, json_reader.GetStat('frames512_1023'))
    type(self).Frames64.Set(self, json_reader.GetStat('frames64'))
    type(self).Frames65_127.Set(self, json_reader.GetStat('frames65_127'))
    type(self).FramesJumbo.Set(self, json_reader.GetStat('framesJumbo'))
    type(self).FramesUndersized.Set(self, json_reader.GetStat(
        'framesUndersized'))
    type(self).Multicast.Set(self, json_reader.GetStat('multicast'))
    type(self).Unicast.Set(self, json_reader.GetStat('unicast'))


class ModemStatus(CATA181GLAUKUS.Modem.Status):
  """Glaukus Manager Modem Status."""

  AbsoluteMse = tr.cwmptypes.ReadOnlyInt()
  AcmEngineRxSensorsEnabled = tr.cwmptypes.ReadOnlyInt()
  AcmEngineTxSwitchEnabled = tr.cwmptypes.ReadOnlyInt()
  AcquireStatus = tr.cwmptypes.ReadOnlyInt()
  AcquireStatusStr = tr.cwmptypes.ReadOnlyString()
  CarrierOffset = tr.cwmptypes.ReadOnlyInt()
  DebugIndications = tr.cwmptypes.ReadOnlyInt()
  ExternalAgc = tr.cwmptypes.ReadOnlyInt()
  InternalAgc = tr.cwmptypes.ReadOnlyInt()
  LastAcquireError = tr.cwmptypes.ReadOnlyInt()
  LastAcquireErrorStr = tr.cwmptypes.ReadOnlyString()
  NormalizedMse = tr.cwmptypes.ReadOnlyInt()
  RadialMse = tr.cwmptypes.ReadOnlyInt()
  ResPhNoiseVal = tr.cwmptypes.ReadOnlyInt()
  RxAcmProfile = tr.cwmptypes.ReadOnlyInt()
  RxSymbolRate = tr.cwmptypes.ReadOnlyInt()
  TxAcmProfile = tr.cwmptypes.ReadOnlyInt()
  TxSymbolRate = tr.cwmptypes.ReadOnlyInt()

  def __init__(self, json_reader):
    super(ModemStatus, self).__init__()
    json_reader.LoadJsonFromFile(MODEM_JSON_FILE, 'status')
    type(self).AbsoluteMse.Set(self, json_reader.GetStat('absoluteMse'))
    type(self).AcmEngineRxSensorsEnabled.Set(self, json_reader.GetStat(
        'acmEngineRxSensorsEnabled'))
    type(self).AcmEngineTxSwitchEnabled.Set(self, json_reader.GetStat(
        'acmEngineTxSwitchEnabled'))
    type(self).AcquireStatus.Set(self, json_reader.GetStat('acquireStatus'))
    type(self).AcquireStatusStr.Set(self, json_reader.GetStat(
        'acquireStatusStr'))
    type(self).CarrierOffset.Set(self, json_reader.GetStat('carrierOffset'))
    type(self).DebugIndications.Set(self, json_reader.GetStat(
        'debugIndications'))
    type(self).ExternalAgc.Set(self, json_reader.GetStat('externalAgc'))
    type(self).InternalAgc.Set(self, json_reader.GetStat('internalAgc'))
    type(self).LastAcquireError.Set(self, json_reader.GetStat(
        'lastAcquireError'))
    type(self).LastAcquireErrorStr.Set(self, json_reader.GetStat(
        'lastAcquireErrorStr'))
    type(self).NormalizedMse.Set(self, json_reader.GetStat('normalizedMse'))
    type(self).RadialMse.Set(self, json_reader.GetStat('radialMse'))
    type(self).ResPhNoiseVal.Set(self, json_reader.GetStat('resPhNoiseVal'))
    type(self).RxAcmProfile.Set(self, json_reader.GetStat('rxAcmProfile'))
    type(self).RxSymbolRate.Set(self, json_reader.GetStat('rxSymbolRate'))
    type(self).TxAcmProfile.Set(self, json_reader.GetStat('txAcmProfile'))
    type(self).TxSymbolRate.Set(self, json_reader.GetStat('txSymbolRate'))


class Radio(CATA181GLAUKUS.Radio):
  """Catawampus implementation of Glaukus Manager Radio statistics."""
  HeaterEnabled = tr.cwmptypes.ReadOnlyBool()
  PaLnaPowerEnabled = tr.cwmptypes.ReadOnlyBool()
  PaLnaPowerStatus = tr.cwmptypes.ReadOnlyString()
  TransceiversPowerEnabled = tr.cwmptypes.ReadOnlyBool()

  @property
  def HiTransceiver(self):
    return RadioHiTransceiver(self.json_reader)

  @property
  def LoTransceiver(self):
    return RadioLoTransceiver(self.json_reader)

  @property
  def Rx(self):
    return RadioRx(self.json_reader)

  @property
  def Tx(self):
    return RadioTx(self.json_reader)

  @property
  def Version(self):
    return RadioVersion(self.json_reader)

  def __init__(self, json_reader):
    super(Radio, self).__init__()
    self.json_reader = json_reader
    json_reader.LoadJsonFromFile(RADIO_JSON_FILE)
    type(self).HeaterEnabled.Set(self, json_reader.GetStat('heaterEnabled'))
    type(self).PaLnaPowerEnabled.Set(self, json_reader.GetStat(
        'paLnaPowerEnabled'))
    type(self).PaLnaPowerStatus.Set(self, json_reader.GetStat(
        'paLnaPowerStatus'))
    type(self).TransceiversPowerEnabled.Set(self, json_reader.GetStat(
        'transceiversPowerEnabled'))


class RadioHiTransceiver(CATA181GLAUKUS.Radio.HiTransceiver):
  """Radio HiTransceiver."""
  IcModel = tr.cwmptypes.ReadOnlyString()
  Mode = tr.cwmptypes.ReadOnlyString()
  Temp = tr.cwmptypes.ReadOnlyInt()

  @property
  def Epot(self):
    return RadioHiEpot(self.json_reader)

  @property
  def Pll(self):
    return RadioHiPll(self.json_reader)

  def __init__(self, json_reader):
    super(RadioHiTransceiver, self).__init__()
    self.json_reader = json_reader
    json_reader.LoadJsonFromFile(RADIO_JSON_FILE, 'hiTransceiver')
    type(self).IcModel.Set(self, json_reader.GetStat('icModel'))
    type(self).Mode.Set(self, json_reader.GetStat('mode'))
    type(self).Temp.Set(self, json_reader.GetStat('temp'))


class RadioHiEpot(CATA181GLAUKUS.Radio.HiTransceiver.Epot):
  """Radio HiTransceiver Epot."""
  Control = tr.cwmptypes.ReadOnlyString()
  Driver = tr.cwmptypes.ReadOnlyInt()
  Lna = tr.cwmptypes.ReadOnlyInt()
  Pa = tr.cwmptypes.ReadOnlyInt()

  def __init__(self, json_reader):
    super(RadioHiEpot, self).__init__()
    json_reader.LoadJsonFromFile(RADIO_JSON_FILE, 'hiTransceiver.epot')
    type(self).Control.Set(self, json_reader.GetStat('control'))
    type(self).Driver.Set(self, json_reader.GetStat('driver'))
    type(self).Lna.Set(self, json_reader.GetStat('lna'))
    type(self).Pa.Set(self, json_reader.GetStat('pa'))


class RadioHiPll(CATA181GLAUKUS.Radio.HiTransceiver.Pll):
  """Radio HiTransceiver Pll."""
  Frequency = tr.cwmptypes.ReadOnlyInt()
  LockCounts = tr.cwmptypes.ReadOnlyInt()
  Locked = tr.cwmptypes.ReadOnlyBool()

  def __init__(self, json_reader):
    super(RadioHiPll, self).__init__()
    json_reader.LoadJsonFromFile(RADIO_JSON_FILE, 'hiTransceiver.pll')
    type(self).Frequency.Set(self, json_reader.GetStat('frequency'))
    type(self).LockCounts.Set(self, json_reader.GetStat('lockCounts'))
    type(self).Locked.Set(self, json_reader.GetStat('locked'))


class RadioLoTransceiver(CATA181GLAUKUS.Radio.LoTransceiver):
  """Radio LoTransceiver."""
  IcModel = tr.cwmptypes.ReadOnlyString()
  Mode = tr.cwmptypes.ReadOnlyString()
  Temp = tr.cwmptypes.ReadOnlyInt()

  @property
  def Epot(self):
    return RadioLoEpot(self.json_reader)

  @property
  def Pll(self):
    return RadioLoPll(self.json_reader)

  def __init__(self, json_reader):
    super(RadioLoTransceiver, self).__init__()
    self.json_reader = json_reader
    json_reader.LoadJsonFromFile(RADIO_JSON_FILE, 'loTransceiver')
    type(self).IcModel.Set(self, json_reader.GetStat('icModel'))
    type(self).Mode.Set(self, json_reader.GetStat('mode'))
    type(self).Temp.Set(self, json_reader.GetStat('temp'))


class RadioLoEpot(CATA181GLAUKUS.Radio.LoTransceiver.Epot):
  """Radio LoTransceiver Epot."""
  Control = tr.cwmptypes.ReadOnlyString()
  Driver = tr.cwmptypes.ReadOnlyInt()
  Lna = tr.cwmptypes.ReadOnlyInt()
  Pa = tr.cwmptypes.ReadOnlyInt()

  def __init__(self, json_reader):
    super(RadioLoEpot, self).__init__()
    json_reader.LoadJsonFromFile(RADIO_JSON_FILE, 'loTransceiver.epot')
    type(self).Control.Set(self, json_reader.GetStat('control'))
    type(self).Driver.Set(self, json_reader.GetStat('driver'))
    type(self).Lna.Set(self, json_reader.GetStat('lna'))
    type(self).Pa.Set(self, json_reader.GetStat('pa'))


class RadioLoPll(CATA181GLAUKUS.Radio.LoTransceiver.Pll):
  """Radio LoTransceiver Pll."""
  Frequency = tr.cwmptypes.ReadOnlyInt()
  LockCounts = tr.cwmptypes.ReadOnlyInt()
  Locked = tr.cwmptypes.ReadOnlyBool()

  def __init__(self, json_reader):
    super(RadioLoPll, self).__init__()
    json_reader.LoadJsonFromFile(RADIO_JSON_FILE, 'loTransceiver.pll')
    type(self).Frequency.Set(self, json_reader.GetStat('frequency'))
    type(self).LockCounts.Set(self, json_reader.GetStat('lockCounts'))
    type(self).Locked.Set(self, json_reader.GetStat('locked'))


class RadioRx(CATA181GLAUKUS.Radio.Rx):
  """Glaukus Manager Radio RX."""
  AgcDigitalGain = tr.cwmptypes.ReadOnlyInt()
  AgcDigitalGainIndex = tr.cwmptypes.ReadOnlyInt()
  LnaCurrentMeas = tr.cwmptypes.ReadOnlyInt()
  LnaCurrentSet = tr.cwmptypes.ReadOnlyInt()
  Rssi = tr.cwmptypes.ReadOnlyInt()

  def __init__(self, json_reader):
    super(RadioRx, self).__init__()
    json_reader.LoadJsonFromFile(RADIO_JSON_FILE, 'rx')
    type(self).AgcDigitalGain.Set(self, json_reader.GetStat('agcDigitalGain'))
    type(self).AgcDigitalGainIndex.Set(self, json_reader.GetStat(
        'agcDigitalGainIndex'))
    type(self).LnaCurrentMeas.Set(self, json_reader.GetStat('lnaCurrentMeas'))
    type(self).LnaCurrentSet.Set(self, json_reader.GetStat('lnaCurrentSet'))
    type(self).Rssi.Set(self, json_reader.GetStat('rssi'))


class RadioTx(CATA181GLAUKUS.Radio.Tx):
  """Glaukus Manager Radio TX."""
  DcI = tr.cwmptypes.ReadOnlyInt()
  DcQ = tr.cwmptypes.ReadOnlyInt()
  DriverCurrentMeas = tr.cwmptypes.ReadOnlyInt()
  DriverCurrentSet = tr.cwmptypes.ReadOnlyInt()
  PaCurrentMeas = tr.cwmptypes.ReadOnlyInt()
  PaCurrentSet = tr.cwmptypes.ReadOnlyInt()
  PaTemp = tr.cwmptypes.ReadOnlyInt()
  TxPowerControl = tr.cwmptypes.ReadOnlyString()
  TxPowerMeas = tr.cwmptypes.ReadOnlyInt()
  TxPowerSet = tr.cwmptypes.ReadOnlyInt()
  VgaGain = tr.cwmptypes.ReadOnlyInt()

  def __init__(self, json_reader):
    super(RadioTx, self).__init__()
    json_reader.LoadJsonFromFile(RADIO_JSON_FILE, 'tx')
    type(self).DcI.Set(self, json_reader.GetStat('dcI'))
    type(self).DcQ.Set(self, json_reader.GetStat('dcQ'))
    type(self).DriverCurrentMeas.Set(self, json_reader.GetStat(
        'driverCurrentMeas'))
    type(self).DriverCurrentSet.Set(self, json_reader.GetStat(
        'driverCurrentSet'))
    type(self).PaCurrentMeas.Set(self, json_reader.GetStat('paCurrentMeas'))
    type(self).PaCurrentSet.Set(self, json_reader.GetStat('paCurrentSet'))
    type(self).PaTemp.Set(self, json_reader.GetStat('paTemp'))
    type(self).TxPowerControl.Set(self, json_reader.GetStat('txPowerControl'))
    type(self).TxPowerMeas.Set(self, json_reader.GetStat('txPowerMeas'))
    type(self).TxPowerSet.Set(self, json_reader.GetStat('txPowerSet'))
    type(self).VgaGain.Set(self, json_reader.GetStat('vgaGain'))


class RadioVersion(CATA181GLAUKUS.Radio.Version):
  """Glaukus Manager Radio Version."""

  @property
  def Hardware(self):
    return RadioVersionHardware(self.json_reader)

  @property
  def Software(self):
    return RadioVersionSoftware(self.json_reader)

  def __init__(self, json_reader):
    super(RadioVersion, self).__init__()
    self.json_reader = json_reader


class RadioVersionHardware(CATA181GLAUKUS.Radio.Version.Hardware):
  """Glaukus Manager Radio Version Hardware."""
  Major = tr.cwmptypes.ReadOnlyInt()
  Minor = tr.cwmptypes.ReadOnlyInt()
  Type = tr.cwmptypes.ReadOnlyString()

  def __init__(self, json_reader):
    super(RadioVersionHardware, self).__init__()
    json_reader.LoadJsonFromFile(RADIO_JSON_FILE, 'version.hardware')
    type(self).Major.Set(self, json_reader.GetStat('major'))
    type(self).Minor.Set(self, json_reader.GetStat('minor'))
    type(self).Type.Set(self, json_reader.GetStat('type'))


class RadioVersionSoftware(CATA181GLAUKUS.Radio.Version.Software):
  """Glaukus Manager Radio Version Software."""
  Build = tr.cwmptypes.ReadOnlyInt()
  Major = tr.cwmptypes.ReadOnlyInt()
  Minor = tr.cwmptypes.ReadOnlyInt()

  def __init__(self, json_reader):
    super(RadioVersionSoftware, self).__init__()
    json_reader.LoadJsonFromFile(RADIO_JSON_FILE, 'version.software')
    type(self).Build.Set(self, json_reader.GetStat('build'))
    type(self).Major.Set(self, json_reader.GetStat('major'))
    type(self).Minor.Set(self, json_reader.GetStat('minor'))


if __name__ == '__main__':
  print tr.handle.DumpSchema(Glaukus())

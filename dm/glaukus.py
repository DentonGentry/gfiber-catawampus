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
REPORT_JSON_FILE = '/tmp/glaukus/report.json'


class JsonReader(object):
  """Converts JSON files to Python objects."""

  def __init__(self):
    self._json_data = {}

  def LoadJsonFromFile(self, path, json_stats_key):
    """Deserializes a JSON file to a Python object.

    Args:
      path: The path to the JSON file to be converted.
      json_stats_key: The key used to extract relevant section of data from the
                      from the JSON object.

    Raises:
      ValueError: If the JSON data loaded from the file does not contain the
                  requested key, a ValueError is raised.
    """
    self._json_data = {}
    if not os.path.exists(path):
      # It is a valid state that there might not be a JSON data file yet.
      return

    try:
      with open(path) as f:
        json_data = json.load(f)
      if not json_data.has_key(json_stats_key):
        raise ValueError('JSON data does not have key: %s' % json_stats_key)
      self._json_data = json_data[json_stats_key]
    except (IOError, OSError) as ex:
      print 'Failed to load %s: %s' % (path, ex)
      return
    except ValueError as ex:
      # Limit output length or logos will clip the line.
      print 'Failed to decode JSON! path:%s, content:%s, %s' % (
          path, str(json_data)[0:70], ex)
      return

  def GetStat(self, attr, default=0):
    return self._json_data.get(attr, default)


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

  @property
  def Report(self):
    return Report(self.json_reader)


class Modem(CATA181GLAUKUS.Modem):
  """Catawampus implementation of Glaukus Manager Modem statistics."""

  ChipTemp = tr.cwmptypes.ReadOnlyFloat()
  ChipTempStatus = tr.cwmptypes.ReadOnlyString()
  ConfigHash = tr.cwmptypes.ReadOnlyString()
  FecAlarms = tr.cwmptypes.ReadOnlyInt()
  PcbCurrentDraw = tr.cwmptypes.ReadOnlyFloat()
  PcbTemp = tr.cwmptypes.ReadOnlyFloat()
  PcbTempStatus = tr.cwmptypes.ReadOnlyString()
  ResetCount = tr.cwmptypes.ReadOnlyUnsigned()
  Uptime = tr.cwmptypes.ReadOnlyUnsigned()

  def __init__(self, json_reader):
    super(Modem, self).__init__()
    json_reader.LoadJsonFromFile(MODEM_JSON_FILE, 'modem')
    type(self).ChipTemp.Set(self, json_reader.GetStat('chip_temp'))
    type(self).ChipTempStatus.Set(
        self, json_reader.GetStat('chip_temp_status'))
    type(self).ConfigHash.Set(self, json_reader.GetStat('config_hash'))
    type(self).FecAlarms.Set(self, json_reader.GetStat('fec_alarms'))
    type(self).PcbCurrentDraw.Set(
        self, json_reader.GetStat('pcb_current_draw'))
    type(self).PcbTemp.Set(self, json_reader.GetStat('pcb_temp'))
    type(self).PcbTempStatus.Set(self, json_reader.GetStat('pcb_temp_status'))
    type(self).ResetCount.Set(self, json_reader.GetStat('reset_count'))
    type(self).Uptime.Set(self, json_reader.GetStat('uptime'))


class Radio(CATA181GLAUKUS.Radio):
  """Catawampus implementation of Glaukus Manager Radio statistics."""

  MajorVersion = tr.cwmptypes.ReadOnlyString()
  MinorVersion = tr.cwmptypes.ReadOnlyString()

  def __init__(self, json_reader):
    super(Radio, self).__init__()
    json_reader.LoadJsonFromFile(RADIO_JSON_FILE, 'radio')
    type(self).MajorVersion.Set(self, json_reader.GetStat('major_version'))
    type(self).MinorVersion.Set(self, json_reader.GetStat('minor_version'))


class Report(CATA181GLAUKUS.Report):
  """Catawampus implementation of Glaukus Manager Report statistics."""

  AbsMseDb = tr.cwmptypes.ReadOnlyInt()
  AdcCount = tr.cwmptypes.ReadOnlyInt()
  ExternalAgcIdx = tr.cwmptypes.ReadOnlyInt()
  InPowerRssiDbc = tr.cwmptypes.ReadOnlyInt()
  InbandPowerRssiDbc = tr.cwmptypes.ReadOnlyInt()
  InternalAgcIdx = tr.cwmptypes.ReadOnlyInt()
  MeasuredPowerRssiDbm = tr.cwmptypes.ReadOnlyInt()
  NormMseDb = tr.cwmptypes.ReadOnlyInt()
  RadMseDb = tr.cwmptypes.ReadOnlyInt()
  RxLockLossEvents = tr.cwmptypes.ReadOnlyUnsigned()
  RxLockLossTimeMs = tr.cwmptypes.ReadOnlyUnsigned()
  RxLockStatus = tr.cwmptypes.ReadOnlyBool()
  StartSampleCaptureTimeMs = tr.cwmptypes.ReadOnlyUnsigned()
  StopSampleCaptureTimeMs = tr.cwmptypes.ReadOnlyUnsigned()

  def __init__(self, json_reader):
    super(Report, self).__init__()
    json_reader.LoadJsonFromFile(REPORT_JSON_FILE, 'report')
    type(self).AbsMseDb.Set(self, json_reader.GetStat('abs_mse_db'))
    type(self).AdcCount.Set(self, json_reader.GetStat('adc_count'))
    type(self).ExternalAgcIdx.Set(
        self, json_reader.GetStat('external_agc_idx'))
    type(self).InPowerRssiDbc.Set(
        self, json_reader.GetStat('inpower_rssi_dbc'))
    type(self).InbandPowerRssiDbc.Set(
        self, json_reader.GetStat('inband_power_rssi_dbc'))
    type(self).InternalAgcIdx.Set(
        self, json_reader.GetStat('internal_agc_idx'))
    type(self).MeasuredPowerRssiDbm.Set(
        self, json_reader.GetStat('msr_pwr_rssi_dbm'))
    type(self).NormMseDb.Set(self, json_reader.GetStat('norm_mse_db'))
    type(self).RadMseDb.Set(self, json_reader.GetStat('rad_mse_db'))
    type(self).RxLockLossEvents.Set(
        self, json_reader.GetStat('rx_lock_loss_events'))
    type(self).RxLockLossTimeMs.Set(
        self, json_reader.GetStat('rx_lock_loss_time_ms'))
    type(self).RxLockStatus.Set(self, json_reader.GetStat('rx_lock_status'))
    type(self).StartSampleCaptureTimeMs.Set(
        self, json_reader.GetStat('sample_start_tstamp_ms'))
    type(self).StopSampleCaptureTimeMs.Set(
        self, json_reader.GetStat('sample_stop_tstamp_ms'))


if __name__ == '__main__':
  print tr.handle.DumpSchema(Glaukus())

#!/usr/bin/python
# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Implementation of TR-69 objects for Prestera switch."""

__author__ = 'poist@google.com (Gregory Poist)'

import json
import os
import google3
import tr.basemodel
import tr.cwmptypes

ETHERNET = tr.basemodel.Device.Ethernet

PORTS_JSON_FILE = '/tmp/prestera/ports.json'


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

  def GetStat(self, value, default='0'):
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


class EthernetInterfaceStatsPrestera(ETHERNET.Interface.Stats):
  """tr181 Ethernet.Interface.{i}.Stats implementation for Prestera 0/#."""

  def __init__(self, ifname):
    super(EthernetInterfaceStatsPrestera, self).__init__()

    self.ifname = ifname
    self.json_reader = JsonReader()

    port = 0
    if ifname.startswith('lan'):
      port = ifname[3:]
    self.port_path = 'port-interface-statistics.0/' + port

    self.Unexport(['X_CATAWAMPUS-ORG_DiscardFrameCnts',
                   'X_CATAWAMPUS-ORG_DiscardPacketsReceivedHipri'])

  @property
  def BytesSent(self):
    self.json_reader.LoadJsonFromFile(PORTS_JSON_FILE, self.port_path)
    return self.json_reader.GetStat('goodOctetsSent')

  @property
  def BytesReceived(self):
    self.json_reader.LoadJsonFromFile(PORTS_JSON_FILE, self.port_path)
    try:
      return str(int(self.json_reader.GetStat('goodOctetsRcv')) +
                 int(self.json_reader.GetStat('badOctetsRcv')))
    except ValueError:
      return '0'

  @property
  def PacketsSent(self):
    self.json_reader.LoadJsonFromFile(PORTS_JSON_FILE, self.port_path)
    try:
      return str(int(self.json_reader.GetStat('brdcPktsSent')) +
                 int(self.json_reader.GetStat('mcPktsSent')) +
                 int(self.json_reader.GetStat('ucPktsSent')))
    except ValueError:
      return '0'

  @property
  def PacketsReceived(self):
    self.json_reader.LoadJsonFromFile(PORTS_JSON_FILE, self.port_path)
    try:
      return str(int(self.json_reader.GetStat('brdcPktsRcv')) +
                 int(self.json_reader.GetStat('mcPktsRcv')) +
                 int(self.json_reader.GetStat('ucPktsRcv')))
    except ValueError:
      return '0'

  @property
  def ErrorsSent(self):
    self.json_reader.LoadJsonFromFile(PORTS_JSON_FILE, self.port_path)
    return self.json_reader.GetStat('macTransmitErr')

  @property
  def ErrorsReceived(self):
    self.json_reader.LoadJsonFromFile(PORTS_JSON_FILE, self.port_path)
    try:
      return str(int(self.json_reader.GetStat('macRcvError')) +
                 int(self.json_reader.GetStat('jabberPkts')) +
                 int(self.json_reader.GetStat('oversizePkts')))
    except ValueError:
      return '0'

  @property
  def UnicastPacketsSent(self):
    self.json_reader.LoadJsonFromFile(PORTS_JSON_FILE, self.port_path)
    return self.json_reader.GetStat('ucPktsSent')

  @property
  def UnicastPacketsReceived(self):
    self.json_reader.LoadJsonFromFile(PORTS_JSON_FILE, self.port_path)
    return self.json_reader.GetStat('ucPktsRcv')

  @property
  def DiscardPacketsSent(self):
    return '0'  # No analogous statistic in source.

  @property
  def DiscardPacketsReceived(self):
    return '0'  # No analogous statistic in source.

  @property
  def MulticastPacketsSent(self):
    self.json_reader.LoadJsonFromFile(PORTS_JSON_FILE, self.port_path)
    return self.json_reader.GetStat('mcPktsSent')

  @property
  def MulticastPacketsReceived(self):
    self.json_reader.LoadJsonFromFile(PORTS_JSON_FILE, self.port_path)
    return self.json_reader.GetStat('mcPktsRcv')

  @property
  def BroadcastPacketsSent(self):
    self.json_reader.LoadJsonFromFile(PORTS_JSON_FILE, self.port_path)
    return self.json_reader.GetStat('brdcPktsSent')

  @property
  def BroadcastPacketsReceived(self):
    self.json_reader.LoadJsonFromFile(PORTS_JSON_FILE, self.port_path)
    return self.json_reader.GetStat('brdcPktsRcv')

  @property
  def UnknownProtoPacketsReceived(self):
    return '0'  # No analogous statistic in source.


class EthernetInterfacePrestera(ETHERNET.Interface):
  """Handling for Status of a Prestera switch port.

  Switch status is fixed configuration at this point.

  Args:
    ifname: netdev name, like 'lanN' where N is the switch port number.
  """

  Enable = tr.cwmptypes.ReadOnlyBool(True)
  Status = tr.cwmptypes.ReadOnlyString('')
  LowerLayers = tr.cwmptypes.ReadOnlyString('')
  Name = tr.cwmptypes.ReadOnlyString('')
  Upstream = tr.cwmptypes.ReadOnlyBool(False)
  MaxBitRate = tr.cwmptypes.ReadOnlyInt(0)
  DuplexMode = tr.cwmptypes.ReadOnlyString('')
  X_CATAWAMPUS_ORG_ActualBitRate = tr.cwmptypes.ReadOnlyInt(0)
  X_CATAWAMPUS_ORG_ActualDuplexMode = tr.cwmptypes.ReadOnlyString('')

  def __init__(self, ifname):
    super(EthernetInterfacePrestera, self).__init__()

    self._ifname = ifname
    self.Unexport(['Alias', 'LastChange', 'MACAddress'])
    type(self).Status.Set(self, 'Up')
    type(self).Name.Set(self, ifname)
    type(self).Upstream.Set(self, False)
    if ifname == 'lan0' or ifname == 'lan4':
      type(self).MaxBitRate.Set(self, 1000)
      type(self).X_CATAWAMPUS_ORG_ActualBitRate = 1000
    else:
      type(self).MaxBitRate.Set(self, 10000)
      type(self).X_CATAWAMPUS_ORG_ActualBitRate = 10000
    type(self).DuplexMode.Set(self, 'Full')
    type(self).X_CATAWAMPUS_ORG_ActualDuplexMode = 'Full'
    self._Stats = EthernetInterfaceStatsPrestera(ifname=ifname)

  @property
  def Stats(self):
    return self._Stats

  # All the values other than Stats are static

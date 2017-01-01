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
# pylint:disable=invalid-name

"""Implementation tr-181 Device.Ethernet for QCA83xx switches.

Handles the Device.Ethernet portion of TR-181, as described
in http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import datetime
import json
import tr.basemodel
import tr.cwmptypes
import tr.session


ETHERNET = tr.basemodel.Device.Ethernet
QCA83XX_JSON = ['/tmp/qca83xx.json']


class EthernetInterfaceStatsQca83xx(ETHERNET.Interface.Stats):
  """tr181 Ethernet.Interface.{i}.Stats implementation for qca83xx."""

  BroadcastPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(0)
  BroadcastPacketsSent = tr.cwmptypes.ReadOnlyUnsigned(0)
  BytesReceived = tr.cwmptypes.ReadOnlyUnsigned(0)
  BytesSent = tr.cwmptypes.ReadOnlyUnsigned(0)
  DiscardPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(0)
  DiscardPacketsSent = tr.cwmptypes.ReadOnlyUnsigned(0)
  ErrorsReceived = tr.cwmptypes.ReadOnlyUnsigned(0)
  ErrorsSent = tr.cwmptypes.ReadOnlyUnsigned(0)
  MulticastPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(0)
  MulticastPacketsSent = tr.cwmptypes.ReadOnlyUnsigned(0)
  PacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(0)
  PacketsSent = tr.cwmptypes.ReadOnlyUnsigned(0)
  UnicastPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(0)
  UnicastPacketsSent = tr.cwmptypes.ReadOnlyUnsigned(0)
  UnknownProtoPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(0)
  X_CATAWAMPUS_ORG_DiscardFrameCnts = tr.cwmptypes.ReadOnlyUnsigned(0)

  def __init__(self, stats):
    super(EthernetInterfaceStatsQca83xx, self).__init__()
    self.Unexport(['X_CATAWAMPUS-ORG_DiscardFrameCnts',
                   'X_CATAWAMPUS-ORG_DiscardPacketsReceivedHipri'])
    type(self).BytesReceived.Set(self, stats.get('BytesReceived', 0))
    rx_unicast_pkts = stats.get('UnicastPacketsReceived', 0)
    rx_multicast_pkts = stats.get('MulticastPacketsReceived', 0)
    rx_broadcast_pkts = stats.get('BroadcastPacketsReceived', 0)
    rx_pkts = rx_unicast_pkts + rx_multicast_pkts + rx_broadcast_pkts
    type(self).PacketsReceived.Set(self, rx_pkts)
    type(self).UnicastPacketsReceived.Set(self, rx_unicast_pkts)
    type(self).MulticastPacketsReceived.Set(self, rx_multicast_pkts)
    type(self).BroadcastPacketsReceived.Set(self, rx_broadcast_pkts)
    type(self).ErrorsReceived.Set(self, stats.get('ErrorsReceived', 0))

    type(self).BytesSent.Set(self, stats.get('BytesSent', 0))
    tx_unicast_pkts = stats.get('UnicastPacketsSent', 0)
    tx_multicast_pkts = stats.get('MulticastPacketsSent', 0)
    tx_broadcast_pkts = stats.get('BroadcastPacketsSent', 0)
    tx_pkts = tx_unicast_pkts + tx_multicast_pkts + tx_broadcast_pkts
    type(self).PacketsSent.Set(self, tx_pkts)
    type(self).UnicastPacketsSent.Set(self, tx_unicast_pkts)
    type(self).MulticastPacketsSent.Set(self, tx_multicast_pkts)
    type(self).BroadcastPacketsSent.Set(self, tx_broadcast_pkts)
    type(self).ErrorsSent.Set(self, stats.get('ErrorsSent', 0))


class EthernetInterfaceQca83xx(ETHERNET.Interface):
  """Handling for a QCA83xx switch port.

  Args:
    portnum: the 1-based port number on the switch chip.
    mac: the MAC address of this port. The QCA83xx doesn't know it.
    upstream: whether the port faces the WAN (unlikely).
  """

  Enable = tr.cwmptypes.ReadOnlyBool(True)
  LowerLayers = tr.cwmptypes.ReadOnlyString('')
  MACAddress = tr.cwmptypes.ReadOnlyMacAddr('')
  Name = tr.cwmptypes.ReadOnlyString('')
  Upstream = tr.cwmptypes.ReadOnlyBool(False)

  def __init__(self, portnum, mac, upstream=False):
    super(EthernetInterfaceQca83xx, self).__init__()
    self._portnum = portnum
    self.Unexport(['Alias'])
    type(self).MACAddress.Set(self, mac)
    type(self).Name.Set(self, 'lan0:' + str(portnum))
    type(self).Upstream.Set(self, upstream)
    self.stats = {}

  @tr.session.cache
  def _GetJsonPortInfo(self):
    """Read in information about this port from JSON.

      The Ports section of the file looks like:
      # cat /tmp/qca83xx.json
      {
        "Ports": [
          {
            "PortName": "lan0:1",
            "LinkSpeed": 0,
            "LinkDuplex": "Unknown",
            "LinkStatus": "Down",
            "LastChanged": 0,
            "BytesReceived": 0,
            "ErrorsReceived": 0,
            "UnicastPacketsReceived": 0,
            "MulticastPacketsReceived": 0,
            "BroadcastPacketsReceived": 0,
            "BytesSent": 0,
            "ErrorsSent": 0,
            "UnicastPacketsSent": 0,
            "MulticastPacketsSent": 0,
            "BroadcastPacketsSent": 0,
            "CableStatus": "OK",
            "CableLength": 0
          },

    Returns:
        a dict of the contents of this port in the JSON file.
    """
    try:
      js = json.load(open(QCA83XX_JSON[0]))
    except (IOError, ValueError):
      return {}
    ports = js.get('Ports', [])
    for port in ports:
      if port.get('PortName', '') == self.Name:
        return port
    return {}

  @property
  def LastChange(self):
    seconds_since_epoch = self._GetJsonPortInfo().get('LastChanged', 0)
    dt = datetime.datetime.utcfromtimestamp(seconds_since_epoch)
    return tr.cwmpdate.format(dt)

  @property
  def Status(self):
    linkstatus = self._GetJsonPortInfo().get('LinkStatus', 'Error')
    if linkstatus == 'Up':
      return 'Up'
    cablestatus = self._GetJsonPortInfo().get('CableStatus', 'OK')
    if cablestatus == 'SH' or cablestatus == 'IV':
      return 'Error'
    return 'Down'

  @property
  def Stats(self):
    return EthernetInterfaceStatsQca83xx(self._GetJsonPortInfo())

  @property
  def MaxBitRate(self):
    return self._GetJsonPortInfo().get('LinkSpeed', 0)

  @property
  def X_CATAWAMPUS_ORG_ActualBitRate(self):
    return self._GetJsonPortInfo().get('LinkSpeed', 0)

  @property
  def DuplexMode(self):
    return self._GetJsonPortInfo().get('LinkDuplex', 'Half')

  @property
  def X_CATAWAMPUS_ORG_ActualDuplexMode(self):
    return self._GetJsonPortInfo().get('LinkDuplex', 'Half')

  def GetAssociatedDevices(self):
    """Return a list of known clients of this interface.

      The Fdb section of the JSON file looks like:
      "Fdb": [
        {
          "PhysAddress": "00:01:02:03:04:05",
          "PortList": [ "lan0:2" ]
        },
        {
          "PhysAddress": "00:01:02:03:04:06",
          "PortList": [ "lan0:3" ]
        },

    Returns:
      a list of dicts, where the dict contains a
      'PhysAddress' key with the MAC address.
    """
    js = {}
    result = []
    try:
      js = json.load(open(QCA83XX_JSON[0]))
    except (IOError, ValueError):
      return {}
    fdb = js.get('Fdb', [])
    for station in fdb:
      macaddr = station.get('PhysAddress', '')
      portlist = station.get('PortList', [])
      if macaddr and self.Name in portlist:
        octets = macaddr.split(':')
        b1 = int(octets[0], 16)
        if not b1 & 0x01:
          # only report unicast addresses, not multicast
          result.append({'PhysAddress': macaddr})
    return result

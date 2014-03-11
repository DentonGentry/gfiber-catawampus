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
# pylint: disable-msg=C6409
# pylint: disable-msg=W0404
#

"""Implement the tr181 Ethernet.Status data model for marvel 88601."""

__author__ = 'jnewlin@google.com (John Newlin)'

import google3
import tr.types
import tr.tr181_v2_6

ETHERNET = tr.tr181_v2_6.Device_v2_6.Device.Ethernet


class NetdevStatsMrvl88601(ETHERNET.Interface.Stats):
  """Parses mrvl stats to populate Stats objects in several TRs."""

  BroadcastPacketsReceived = tr.types.ReadOnlyUnsigned(0)
  BroadcastPacketsSent = tr.types.ReadOnlyUnsigned(0)
  BytesReceived = tr.types.ReadOnlyUnsigned(0)
  BytesSent = tr.types.ReadOnlyUnsigned(0)
  DiscardPacketsReceived = tr.types.ReadOnlyUnsigned(0)
  DiscardPacketsSent = tr.types.ReadOnlyUnsigned(0)
  ErrorsReceived = tr.types.ReadOnlyUnsigned(0)
  ErrorsSent = tr.types.ReadOnlyUnsigned(0)
  MulticastPacketsReceived = tr.types.ReadOnlyUnsigned(0)
  MulticastPacketsSent = tr.types.ReadOnlyUnsigned(0)
  PacketsReceived = tr.types.ReadOnlyUnsigned(0)
  PacketsSent = tr.types.ReadOnlyUnsigned(0)
  UnicastPacketsReceived = tr.types.ReadOnlyUnsigned(0)
  UnicastPacketsSent = tr.types.ReadOnlyUnsigned(0)
  UnknownProtoPacketsReceived = tr.types.ReadOnlyUnsigned(0)

  def __init__(self, stat_dir):
    """Read network interface stats from sysfs.

    Args:
      stat_dir: The direcotry that contains the exported network stats.
    """
    super(NetdevStatsMrvl88601, self).__init__()
    self.stat_dir = stat_dir

    rx_good_octets = self._ReadStatFile('rx_good_octets')
    rx_good_pkts = self._ReadStatFile('rx_good_packets')
    rx_broadcast_pkts = self._ReadStatFile('rx_broadcast_packets')
    rx_multicast_pkts = self._ReadStatFile('rx_multicast_packets')
    tx_good_octets = self._ReadStatFile('tx_good_octets')
    tx_good_pkts = self._ReadStatFile('tx_good_packets')
    tx_broadcast_pkts = self._ReadStatFile('tx_broadcast_packets')
    tx_multicast_pkts = self._ReadStatFile('tx_multicast_packets')

    type(self).BytesReceived.Set(self, rx_good_octets)
    type(self).PacketsReceived.Set(self, rx_good_pkts)
    type(self).MulticastPacketsReceived.Set(self, rx_multicast_pkts)
    type(self).BroadcastPacketsReceived.Set(self, rx_broadcast_pkts)
    type(self).UnicastPacketsReceived.Set(
        self, rx_good_pkts - rx_broadcast_pkts - rx_multicast_pkts)

    type(self).BytesSent.Set(self, tx_good_octets)
    type(self).PacketsSent.Set(self, tx_good_pkts)
    type(self).MulticastPacketsSent.Set(self, tx_multicast_pkts)
    type(self).BroadcastPacketsSent.Set(self, tx_broadcast_pkts)
    type(self).UnicastPacketsSent.Set(
        self, tx_good_pkts - tx_broadcast_pkts - tx_multicast_pkts)

    type(self).ErrorsReceived.Set(self,
        self._ReadStatFile('rx_bad_fc') + self._ReadStatFile('rx_undersized') +
        self._ReadStatFile('rx_fragments') + self._ReadStatFile('rx_oversized') +
        self._ReadStatFile('rx_jabber') + self._ReadStatFile('rx_mac_error') +
        self._ReadStatFile('rx_crc_error') + self._ReadStatFile('rx_bad_packets'))


  def _ReadStatFile(self, stat_file):
    """Read a single network statistic."""
    tmp_name = self.stat_dir + '/' + stat_file
    try:
      with open(tmp_name) as f:
        stat = f.read().strip()
        return long(stat)
    except (IOError, ValueError):
      print 'Cannot get stat from %s' % (tmp_name,)
      return 0

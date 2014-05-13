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

"""Implementation tr-181 Device.Ethernet for QCA83xx switches.

Handles the Device.Ethernet portion of TR-181, as described
in http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import sys
import tr.core
import tr.tr181_v2_6
import tr.types


QCAPORT = None
try:
  import qca83xx
  QCAPORT = qca83xx.Port
except ImportError:
  sys.stderr.write('No qca83xx module; continuing for unit test support.')


ETHERNET = tr.tr181_v2_6.Device_v2_6.Device.Ethernet


class EthernetInterfaceStatsQca83xx(ETHERNET.Interface.Stats):
  """tr181 Ethernet.Interface.{i}.Stats implementation for qca83xx."""

  def __init__(self, stats):
    super(EthernetInterfaceStatsQca83xx, self).__init__()
    self.stats = stats

  def __getattr__(self, name):
    return self.stats.get(name, 0)


class EthernetInterfaceQca83xx(ETHERNET.Interface):
  """Handling for a QCA83xx switch port.

  Args:
    portnum: the 0-based port number on the switch chip.
    mac: the MAC address of this port. The QCA83xx doesn't know it.
    ifname: the Linux netdev handling this switch port
    upstream: whether the port faces the WAN (unlikely).
  """

  Enable = tr.types.ReadOnlyBool(True)
  LowerLayers = tr.types.ReadOnlyString('')
  MACAddress = tr.types.ReadOnlyMacAddr('')
  Name = tr.types.ReadOnlyString('')
  Upstream = tr.types.ReadOnlyBool(False)

  def __init__(self, portnum, mac, ifname, upstream=False):
    super(EthernetInterfaceQca83xx, self).__init__()
    self._portnum = portnum
    self._port = QCAPORT(portnum)
    self._ifname = ifname
    self.Unexport(['Alias'])
    type(self).MACAddress.Set(self, mac)
    type(self).Name.Set(self, 'qca83xx_' + str(portnum))
    type(self).Upstream.Set(self, upstream)
    self.stats = {}

  @property
  def LastChange(self):
    return tr.cwmpdate.format(0)

  @property
  def Status(self):
    if self._port.IsLinkUp():
      return 'Up'
    for (cable_status, unused_cable_len) in self._port.CableDiag():
      if cable_status == 'shorted':
        return 'Error'
    return 'Down'

  @property
  def Stats(self):
    s = self._UpdateStats()
    return EthernetInterfaceStatsQca83xx(s)

  def GetMaxBitRate(self):
    return self._port.Speed()

  def SetMaxBitRate(self, val):
    self._port.Speed(speed=int(val))

  MaxBitRate = property(GetMaxBitRate, SetMaxBitRate, None,
                        'Device.Ethernet.Interface.MaxBitRate')

  def GetDuplexMode(self):
    return self._port.Duplex()

  def SetDuplexMode(self, val):
    self._port.Duplex(duplex=val)

  DuplexMode = property(GetDuplexMode, SetDuplexMode, None,
                        'Device.Ethernet.Interface.DuplexMode')

  def GetAssociatedDevices(self):
    """Return a list of known clients of this interface.

    Returns:
      a list of dicts, where the dict contains:
      1. a 'PhysAddress' key with the MAC address.
      2. an 'IPv4Address' key with a list of IP addresses
         for this mac known by ARP. This list may be empty.
    """
    result = []
    for entry in self._port.Fdb():
      mac = entry['PhysAddress']
      octets = mac.split(':')
      b1 = int(octets[0], 16)
      if not b1 & 0x01:
        # only report unicast addresses, not multicast
        result.append({'PhysAddress': mac})
    return result

  def _UpdateStats(self):
    """Accumulate MIB counters from the hardware.

    The QCA83xx clears its MIB counters on read, so we accumulate them
    in software. The hardware has a large number of counters for various
    events, which map to a somewhat smaller number of tr-181 Stats.

    Returns:
      a dict of statistics.
    """
    st = self.stats
    hs = self._port.Stats()
    self._UpdateStat(st, hs, 'BytesSent', 'TxBytes')
    self._UpdateStat(st, hs, 'BytesReceived', 'RxGoodBytes')
    self._UpdateStat(st, hs, 'PacketsSent', 'TxBroadcastPackets')
    self._UpdateStat(st, hs, 'PacketsSent', 'TxMulticastPackets')
    self._UpdateStat(st, hs, 'PacketsSent', 'TxUnicastPackets')
    self._UpdateStat(st, hs, 'PacketsReceived', 'RxBroadcastPackets')
    self._UpdateStat(st, hs, 'PacketsReceived', 'RxMulticastPackets')
    self._UpdateStat(st, hs, 'PacketsReceived', 'RxUnicastPackets')
    self._UpdateStat(st, hs, 'ErrorsSent', 'TxUnderRuns')
    self._UpdateStat(st, hs, 'ErrorsSent', 'TxOverSizePackets')
    self._UpdateStat(st, hs, 'ErrorsSent', 'TxLateCollisions')
    self._UpdateStat(st, hs, 'ErrorsSent', 'TxExcessiveDeferrals')
    self._UpdateStat(st, hs, 'ErrorsReceived', 'RxFcsErrors')
    self._UpdateStat(st, hs, 'ErrorsReceived', 'RxAlignmentErrors')
    self._UpdateStat(st, hs, 'ErrorsReceived', 'RxRuntPackets')
    self._UpdateStat(st, hs, 'ErrorsReceived', 'RxFragments')
    self._UpdateStat(st, hs, 'ErrorsReceived', 'RxTooLongPackets')
    self._UpdateStat(st, hs, 'ErrorsReceived', 'RxOverFlows')
    self._UpdateStat(st, hs, 'UnicastPacketsSent', 'TxUnicastPackets')
    self._UpdateStat(st, hs, 'UnicastPacketsReceived', 'RxUnicastPackets')
    self._UpdateStat(st, hs, 'MulticastPacketsSent', 'TxMulticastPackets')
    self._UpdateStat(st, hs, 'MulticastPacketsReceived', 'RxMulticastPackets')
    self._UpdateStat(st, hs, 'BroadcastPacketsSent', 'TxBroadcastPackets')
    self._UpdateStat(st, hs, 'BroadcastPacketsReceived', 'RxBroadcastPackets')
    return st

  def _UpdateStat(self, swstats, hwstats, swname, hwname):
    """Update accumulator from hardware counter.

    Args
      swstats: a dict containing the accumulated values
      hwstats: a dict of values read from hardware counters
      swname: name of the tr-181 Stat to accumulate into
      hwname: name of the hardware counter to accumulate from
    """
    s = swstats.get(swname, 0L)
    h = long(hwstats.get(hwname, 0))
    swstats[swname] = s + h

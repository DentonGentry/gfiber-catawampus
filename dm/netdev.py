#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
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

"""Implementation of network device support used in a number of data models."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import tr.cwmptypes
import tr.session

# Unit tests can override this.
PROC_NET_DEV = '/proc/net/dev'


class NetdevStatsLinux26(object):
  """Parses /proc/net/dev to populate Stats objects in several TRs."""

  # Fields in /proc/net/dev
  _RX_BYTES = 0
  _RX_PKTS = 1
  _RX_ERRS = 2
  _RX_DROP = 3
  _RX_FIFO = 4
  _RX_FRAME = 5
  _RX_COMPRESSED = 6
  _RX_MCAST = 7
  _TX_BYTES = 8
  _TX_PKTS = 9
  _TX_ERRS = 10
  _TX_DROP = 11
  _TX_FIFO = 12
  _TX_COLLISIONS = 13
  _TX_CARRIER = 14
  _TX_COMPRESSED = 15

  BroadcastPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(0)
  BroadcastPacketsSent = tr.cwmptypes.ReadOnlyUnsigned(0)
  MulticastPacketsSent = tr.cwmptypes.ReadOnlyUnsigned(0)
  UnknownProtoPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(0)

  def __init__(self, ifname, qfiles=None, numq=0, hipriq=0):
    """Parse fields from a /proc/net/dev line.

    Args:
      ifname: string name of the interface, like "eth0"
      qfiles: path to per-queue discard count files
      numq: number of per-queue discard files to look for
      hipriq: number of qfiles to include in DiscardPacketsReceivedHipri
    """
    self.ifname = ifname
    self.qfiles = qfiles
    self.numq = numq
    self.hipriq = hipriq
    self.bytes_received = 0L
    self.bytes_sent = 0L
    self.discards_received = 0L
    self.discards_sent = 0L
    self.errors_received = 0L
    self.errors_sent = 0L
    self.mcast_received = 0L
    self.pkts_received = 0L
    self.pkts_sent = 0L
    self.old_ifstats = [0L, 0L, 0L, 0L, 0L, 0L, 0L, 0L,
                        0L, 0L, 0L, 0L, 0L, 0L, 0L, 0L]

  def Delta(self, new, old):
    """Return the delta between two counter values."""
    if old <= new:
      return new - old
    else:
      return 0xffffffffL - old + new

  @property
  def BytesReceived(self):
    ifstats = self._ReadProcNetDev(self.ifname)
    i = self._RX_BYTES
    self.bytes_received += self.Delta(ifstats[i], self.old_ifstats[i])
    self.old_ifstats[i] = ifstats[i]
    return self.bytes_received

  @property
  def BytesSent(self):
    ifstats = self._ReadProcNetDev(self.ifname)
    i = self._TX_BYTES
    self.bytes_sent += self.Delta(ifstats[i], self.old_ifstats[i])
    self.old_ifstats[i] = ifstats[i]
    return self.bytes_sent

  @property
  def DiscardPacketsReceived(self):
    ifstats = self._ReadProcNetDev(self.ifname)
    i = self._RX_DROP
    self.discards_received += self.Delta(ifstats[i], self.old_ifstats[i])
    self.old_ifstats[i] = ifstats[i]
    i = self._RX_FIFO
    self.discards_received += self.Delta(ifstats[i], self.old_ifstats[i])
    self.old_ifstats[i] = ifstats[i]
    return self.discards_received

  @property
  def DiscardPacketsSent(self):
    ifstats = self._ReadProcNetDev(self.ifname)
    i = self._TX_DROP
    self.discards_sent += self.Delta(ifstats[i], self.old_ifstats[i])
    self.old_ifstats[i] = ifstats[i]
    return self.discards_sent

  @property
  def ErrorsReceived(self):
    ifstats = self._ReadProcNetDev(self.ifname)
    i = self._RX_ERRS
    self.errors_received += self.Delta(ifstats[i], self.old_ifstats[i])
    self.old_ifstats[i] = ifstats[i]
    i = self._RX_FRAME
    self.errors_received += self.Delta(ifstats[i], self.old_ifstats[i])
    self.old_ifstats[i] = ifstats[i]
    return self.errors_received

  @property
  def ErrorsSent(self):
    ifstats = self._ReadProcNetDev(self.ifname)
    i = self._TX_ERRS
    self.errors_sent += self.Delta(ifstats[i], self.old_ifstats[i])
    self.old_ifstats[i] = ifstats[i]
    i = self._TX_FIFO
    self.errors_sent += self.Delta(ifstats[i], self.old_ifstats[i])
    self.old_ifstats[i] = ifstats[i]
    return self.errors_sent

  @property
  def MulticastPacketsReceived(self):
    ifstats = self._ReadProcNetDev(self.ifname)
    i = self._RX_MCAST
    self.mcast_received += self.Delta(ifstats[i], self.old_ifstats[i])
    self.old_ifstats[i] = ifstats[i]
    return self.mcast_received

  @property
  def PacketsReceived(self):
    ifstats = self._ReadProcNetDev(self.ifname)
    i = self._RX_PKTS
    self.pkts_received += self.Delta(ifstats[i], self.old_ifstats[i])
    self.old_ifstats[i] = ifstats[i]
    return self.pkts_received

  @property
  def PacketsSent(self):
    ifstats = self._ReadProcNetDev(self.ifname)
    i = self._TX_PKTS
    self.pkts_sent += self.Delta(ifstats[i], self.old_ifstats[i])
    self.old_ifstats[i] = ifstats[i]
    return self.pkts_sent

  @property
  def UnicastPacketsSent(self):
    return self.PacketsSent

  @property
  def UnicastPacketsReceived(self):
    uni = self.PacketsReceived - self.MulticastPacketsReceived
    if uni < 0:
      # b/12022359 would try to set UnicastPacketsReceived negative, and result
      # in a ValueError. That shouldn't happen any more now that counters
      # are 64 bit, but just in case we check for it here. This is the only
      # stat involving subtraction.
      uni = 0
    return uni

  @property
  def X_CATAWAMPUS_ORG_DiscardFrameCnts(self):
    return self._ReadDiscardStats(self.qfiles, self.numq)

  @property
  def X_CATAWAMPUS_ORG_DiscardPacketsReceivedHipri(self):
    return self._GetHighPrioDiscards(self.X_CATAWAMPUS_ORG_DiscardFrameCnts,
                                     self.hipriq)

  @tr.session.cache
  def _ReadProcNetDev(self, ifname):
    """Return the /proc/net/dev entry for ifname.

    Args:
      ifname: string name of the interface, e.g.: "eth0"

    Returns:
      The /proc/net/dev entry for ifname as a list.
    """
    with open(PROC_NET_DEV) as f:
      for line in f:
        fields = line.split(':')
        if (len(fields) == 2) and (fields[0].strip() == ifname):
          ifstats = fields[1].split()
          return [long(x) for x in ifstats]
    return None

  @tr.session.cache
  def _ReadDiscardStats(self, qfiles, numq):
    """Return the discard counters for ifname.

    Args:
      qfiles: path to per-queue discard count files
      numq: number of per-queue discard files to look for

    Returns:
      A list of all the values in the qfiles, where index
      ranges from 0 to numq (there is a different counter
      for each queue).
    """
    discard_cnts = []
    for i in range(numq):
      try:
        file_path = qfiles % i
        with open(file_path) as f:
          val = long(f.readline().strip())
          discard_cnts.append(val)
      except (IOError, ValueError, TypeError):
        print 'WARN: _ReadDiscardStats %r failed' % (file_path,)
        discard_cnts.append(0)
    return discard_cnts

  def _GetHighPrioDiscards(self, discards, hipriq):
    """Return sum of discards[0:hipriq]."""
    total = 0L
    for i in range(hipriq):
      try:
        total += long(discards[i])
      except (IndexError, ValueError):
        continue
    return total

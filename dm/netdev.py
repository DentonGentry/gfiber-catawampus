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
# pylint: disable-msg=C6409

"""Implementation of network device support used in a number of data models."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import tr.types

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
  _TX_DROP = 10
  _TX_FIFO = 11
  _TX_COLLISIONS = 12
  _TX_CARRIER = 13
  _TX_COMPRESSED = 14

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
  X_CATAWAMPUS_ORG_DiscardPacketsReceivedHipri = tr.types.ReadOnlyUnsigned(0)

  def __init__(self, ifname, qfiles=None, numq=0, hipriq=0):
    """Parse fields from a /proc/net/dev line.

    Args:
      ifname: string name of the interface, like "eth0"
      qfiles: path to per-queue discard count files
      numq: number of per-queue discard files to look for
      hipriq: number of qfiles to include in DiscardPacketsReceivedHipri
    """
    ifstats = self._ReadProcNetDev(ifname)
    if ifstats:
      type(self).BytesReceived.Set(self, long(ifstats[self._RX_BYTES]))
      type(self).BytesSent.Set(self, long(ifstats[self._TX_BYTES]))
      rxdrop = long(ifstats[self._RX_DROP])
      rxfifo = long(ifstats[self._RX_FIFO])
      type(self).DiscardPacketsReceived.Set(self, rxdrop + rxfifo)
      type(self).DiscardPacketsSent.Set(self, long(ifstats[self._TX_DROP]))

      rxerr = long(ifstats[self._RX_ERRS])
      rxframe = long(ifstats[self._RX_FRAME])
      type(self).ErrorsReceived.Set(self, rxerr + rxframe)
      type(self).ErrorsSent.Set(self, long(ifstats[self._TX_FIFO]))
      rxmcast = long(ifstats[self._RX_MCAST])
      rxpkts = long(ifstats[self._RX_PKTS])
      type(self).MulticastPacketsReceived.Set(self, rxmcast)
      type(self).PacketsReceived.Set(self, rxpkts)
      txpkts = long(ifstats[self._TX_PKTS])
      type(self).PacketsSent.Set(self, txpkts)
      rxucast = rxpkts - rxmcast
      if rxucast < 0:
        # Driver probably exports 32 bit counters, and rxpkts wraps first.
        rxucast = 0xffffffff - rxmcast + rxpkts
      type(self).UnicastPacketsReceived.Set(self, rxucast)

      # Linux doesn't break out transmit uni/multi/broadcast, but we don't
      # want to return 0 for all of them. So we return all transmitted
      # packets as unicast, though some were surely multicast or broadcast.
      type(self).UnicastPacketsSent.Set(self, txpkts)
    discards = self._ReadDiscardStats(qfiles, numq)
    self.X_CATAWAMPUS_ORG_DiscardFrameCnts = discards
    h = self._GetHighPrioDiscards(discards, hipriq)
    type(self).X_CATAWAMPUS_ORG_DiscardPacketsReceivedHipri.Set(self, h)

  def _ReadProcNetDev(self, ifname):
    """Return the /proc/net/dev entry for ifname.

    Args:
      ifname: string name of the interface, e.g.: "eth0"

    Returns:
      The /proc/net/dev entry for ifname as a list.
    """
    f = open(PROC_NET_DEV)
    for line in f:
      fields = line.split(':')
      if (len(fields) == 2) and (fields[0].strip() == ifname):
        return fields[1].split()
    f.close()
    return None

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

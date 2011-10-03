#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-181 Device.Ethernet hierarchy of objects.

Handles the Device.Ethernet portion of TR-181, as described
in http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import string
import subprocess
import tr.core
import tr.tr181_v2_2 as tr181

BASEETHERNET = tr181.Device_v2_2.Device.Ethernet

class EthernetInterface(BASEETHERNET.Interface):
  def __init__(self, ifname, upstream,
               path_to_ethtool='/usr/sbin/ethtool'):
    BASEETHERNET.Interface.__init__(self)
    self.Name = ifname
    self.Upstream = upstream
    self.Stats = EthernetInterfaceStatsLinux26(ifname)



class EthernetInterfaceStatsLinux26(BASEETHERNET.Interface.Stats):
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

  def __init__(self, ifname, proc_net_dev='/proc/net/dev'):
    BASEETHERNET.Interface.Stats.__init__(self)
    ifstats = self._ReadProcNetDev(ifname, proc_net_dev)
    self.BroadcastPacketsReceived = None
    self.BroadcastPacketsSent = None
    self.BytesReceived = ifstats[self._RX_BYTES]
    self.BytesSent = ifstats[self._TX_BYTES]
    self.DiscardPacketsReceived = ifstats[self._RX_DROP]
    self.DiscardPacketsSent = ifstats[self._TX_DROP]

    err = int(ifstats[self._RX_ERRS]) + int(ifstats[self._RX_FRAME])
    self.ErrorsReceived = str(err)

    self.ErrorsSent = ifstats[self._TX_FIFO]
    self.MulticastPacketsReceived = ifstats[self._RX_MCAST]
    self.MulticastPacketsSent = None
    self.PacketsReceived = ifstats[self._RX_PKTS]
    self.PacketsSent = ifstats[self._TX_PKTS]

    rx = int(ifstats[self._RX_PKTS]) - int(ifstats[self._RX_MCAST])
    self.UnicastPacketsReceived = str(rx)

    # Linux doesn't break out transmit uni/multi/broadcast, but we don't
    # want to return None for all of them. So we return all transmitted
    # packets as unicast, though some were surely multicast or broadcast.
    self.UnicastPacketsSent = ifstats[self._TX_PKTS]
    self.UnknownProtoPacketsReceived = None

  def _ReadProcNetDev(self, ifname, proc_net_dev):
    f = open(proc_net_dev)
    devices = dict()
    for line in f:
      fields = line.split(':')
      if (len(fields) == 2) and (fields[0].strip() == ifname):
        return fields[1].split()


def main():
  pass

if __name__ == '__main__':
  main()

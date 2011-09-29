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
import tr.core
import tr.tr181_v2_2 as tr181

BASEETHERNET = tr181.Device_v2_2.Device.Ethernet

class EthernetInterface(BASEETHERNET.Interface):
  def __init__(self, ifname, upstream):
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
    self._net_devices = self._ReadProcNetDev(ifname, proc_net_dev)

  def _ReadProcNetDev(self, ifname, proc_net_dev):
    f = open(proc_net_dev)
    devices = dict()
    for line in f:
      fields = line.split(':')
      if (len(fields) == 2) and (fields[0].strip() == ifname):
        self._ifstats = fields[1].split()
    return devices

  def BroadcastPacketsReceived(self):
    return None

  def BroadcastPacketsSent(self):
    # TODO(dgentry) - Linux doesn't track TX Broadcast.
    return None

  def BytesReceived(self):
    return self._ifstats[self._RX_BYTES]

  def BytesSent(self):
    return self._ifstats[self._TX_BYTES]

  def DiscardPacketsReceived(self):
    return self._ifstats[self._RX_DROP]

  def DiscardPacketsSent(self):
    return self._ifstats[self._TX_DROP]

  def ErrorsReceived(self):
    err = int(self._ifstats[self._RX_ERRS]) + int(self._ifstats[self._RX_FRAME])
    return str(err)

  def ErrorsSent(self):
    return self._ifstats[self._TX_FIFO]

  def MulticastPacketsReceived(self):
    return self._ifstats[self._RX_MCAST]

  def MulticastPacketsSent(self):
    return None

  def PacketsReceived(self):
    return self._ifstats[self._RX_PKTS]

  def PacketsSent(self):
    return self._ifstats[self._TX_PKTS]

  def UnicastPacketsReceived(self):
    rx = int(self._ifstats[self._RX_PKTS]) - int(self._ifstats[self._RX_MCAST])
    return str(rx)

  def UnicastPacketsSent(self):
    # Linux doesn't break out transmit uni/multi/broadcast, but we don't
    # want to return None for all of them. So we return all transmitted
    # packets as unicast, though some were surely multicast or broadcast.
    return self._ifstats[self._TX_PKTS]

  def UnknownProtoPacketsReceived(self):
    return None



def main():
  pass

if __name__ == '__main__':
  main()

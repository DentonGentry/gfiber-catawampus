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

BASEDEVICE = tr181.Device_v2_2

class EthernetStatsLinux26(BASEDEVICE.Device.Ethernet.Interface.Stats):
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

  def __init__(self, proc_netdev='/proc/net/dev'):
    BASEDEVICE.Device.Ethernet.Interface.Stats.__init__(self)
    self._net_devices = self._ReadProcNetDev(proc_netdev)

  def _ReadProcNetDev(self, proc_netdev):
    f = open(proc_netdev)
    devices = dict()
    for line in f:
      fields = line.split(':')
      if len(fields) == 2:
        devices[fields[0].strip()] = fields[1].split()
    return devices

  def BroadcastPacketsReceived(self, ifname):
    return None

  def BroadcastPacketsSent(self, ifname):
    # TODO(dgentry) - Linux doesn't track TX Broadcast.
    return None

  def BytesReceived(self, ifname):
    return self._net_devices[ifname][self._RX_BYTES]

  def BytesSent(self, ifname):
    return self._net_devices[ifname][self._TX_BYTES]

  def DiscardPacketsReceived(self, ifname):
    return self._net_devices[ifname][self._RX_DROP]

  def DiscardPacketsSent(self, ifname):
    return self._net_devices[ifname][self._TX_DROP]

  def ErrorsReceived(self, ifname):
    netdev = self._net_devices[ifname]
    errs = int(netdev[self._RX_ERRS]) + int(netdev[self._RX_FRAME])
    return str(errs)

  def ErrorsSent(self, ifname):
    return self._net_devices[ifname][self._TX_FIFO]

  def MulticastPacketsReceived(self, ifname):
    return self._net_devices[ifname][self._RX_MCAST]

  def MulticastPacketsSent(self, ifname):
    return None

  def PacketsReceived(self, ifname):
    return self._net_devices[ifname][self._RX_PKTS]

  def PacketsSent(self, ifname):
    return self._net_devices[ifname][self._TX_PKTS]

  def UnicastPacketsReceived(self, ifname):
    netdev = self._net_devices[ifname]
    uni_rx = int(netdev[self._RX_PKTS]) - int(netdev[self._RX_MCAST])
    return str(uni_rx)

  def UnicastPacketsSent(self, ifname):
    # Linux doesn't break out transmit uni/multi/broadcast, but we don't
    # want to return None for all of them. So we return all transmitted
    # packets as unicast, though some were surely multicast or broadcast.
    return self._net_devices[ifname][self._TX_PKTS]

  def UnknownProtoPacketsReceived(self, ifname):
    return None


def main():
  eth = EthernetStatsLinux26()

if __name__ == '__main__':
  main()

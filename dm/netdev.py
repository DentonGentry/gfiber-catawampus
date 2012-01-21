#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of network device support used in a number of data models."""

__author__ = 'dgentry@google.com (Denton Gentry)'

class NetdevStatsLinux26(object):
  """Parses /proc/net/dev to populate EthernetInterfaceStats

  Args:
    proc_net_dev - string path to /proc/net/dev, allowing unit tests
      to pass in fake data.
  """
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

  def __init__(self, proc_net_dev='/proc/net/dev'):
    self._proc_net_dev = proc_net_dev

  def get_stats(self, ifname, ethstat):
    """Parse fields from a /proc/net/dev line.

    Args:
      ifname - string name of the interface, like "eth0"
      ethstat - object to store EthernetInterfaceStat fields.
    """
    ifstats = self._ReadProcNetDev(ifname, self._proc_net_dev)
    ethstat.BroadcastPacketsReceived = None
    ethstat.BroadcastPacketsSent = None
    ethstat.BytesReceived = ifstats[self._RX_BYTES]
    ethstat.BytesSent = ifstats[self._TX_BYTES]
    ethstat.DiscardPacketsReceived = ifstats[self._RX_DROP]
    ethstat.DiscardPacketsSent = ifstats[self._TX_DROP]

    err = int(ifstats[self._RX_ERRS]) + int(ifstats[self._RX_FRAME])
    ethstat.ErrorsReceived = str(err)

    ethstat.ErrorsSent = ifstats[self._TX_FIFO]
    ethstat.MulticastPacketsReceived = ifstats[self._RX_MCAST]
    ethstat.MulticastPacketsSent = None
    ethstat.PacketsReceived = ifstats[self._RX_PKTS]
    ethstat.PacketsSent = ifstats[self._TX_PKTS]

    rx = int(ifstats[self._RX_PKTS]) - int(ifstats[self._RX_MCAST])
    ethstat.UnicastPacketsReceived = str(rx)

    # Linux doesn't break out transmit uni/multi/broadcast, but we don't
    # want to return None for all of them. So we return all transmitted
    # packets as unicast, though some were surely multicast or broadcast.
    ethstat.UnicastPacketsSent = ifstats[self._TX_PKTS]
    ethstat.UnknownProtoPacketsReceived = None

  def _ReadProcNetDev(self, ifname, proc_net_dev):
    """Return the /proc/net/dev entry for ifname.

    Args:
      ifname - string name of the interface, ecx: "eth0"
      proc_net_dev - string path to /proc/net/dev.
    """
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

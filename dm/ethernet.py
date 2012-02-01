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

import pynetlinux
import tr.core
import tr.tr181_v2_2
import netdev

BASEETHERNET = tr.tr181_v2_2.Device_v2_2.Device.Ethernet


class EthernetInterfaceStatsLinux26(BASEETHERNET.Interface.Stats):
  def __init__(self, ifname):
    BASEETHERNET.Interface.Stats.__init__(self)
    self._netdev = netdev.NetdevStatsLinux26(ifname)

  def __getattr__(self, name):
    if hasattr(self._netdev, name):
      return getattr(self._netdev, name)
    else:
      raise AttributeError


class EthernetInterfaceLinux26(BASEETHERNET.Interface):
  """Handling for a Linux 2.6-style device like eth0/eth1/etc.

  Constructor arguments:
    state - an InterfaceState object for this interface, holding
      configuration state.
    ifstats - a constructor for an EthernetInterfaceStats object
    pynet - an object implementing the pynetlinux ifconfig object.
      This argument allows unit tests to pass in a mock.
  """

  def __init__(self, state, ifstats=None, pynet=None):
    BASEETHERNET.Interface.__init__(self)
    if not pynet:
      pynet = pynetlinux.ifconfig.Interface(state.ifname)
    self._pynet = pynet
    if not ifstats:
      ifstats = EthernetInterfaceStatsLinux26(state.ifname)
    self._ethernet_state = state
    self.Alias = state.ifname
    self.DuplexMode = "Auto"
    self.Enable = True
    self.LastChange = 0  # TODO(dgentry) figure out date format
    self.LowerLayers = None  # Ethernet.Interface is L1, nothing below it.
    self.MaxBitRate = -1
    self.Name = state.ifname
    self.Stats = ifstats
    self.Upstream = state.upstream

  @property
  def MACAddress(self):
    return self._pynet.get_mac()

  @property
  def Status(self):
    if not self._pynet.is_up():
      return "Down"
    (speed, duplex, auto, link_up) = self._pynet.get_link_info()
    if link_up:
      return "Up"
    else:
      return "Dormant"


class EthernetState(object):
  def __init__(self, ifname, upstream, iftype):
    self.ifname = ifname
    self.upstream = upstream
    self.iftype = iftype


class Ethernet(BASEETHERNET):
  def __init__(self):
    BASEETHERNET.__init__(self)
    self.InterfaceList = tr.core.AutoDict(
        'InterfaceList', iteritems=self.IterInterfaces,
        getitem=self.GetInterface)
    self._Interfaces = {}
    self._NextInterface = 0
    self.LinkList = {}
    self.VLANTerminationList = {}

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)

  @property
  def LinkNumberOfEntries(self):
    return len(self.LinkList)

  @property
  def VLANTerminationNumberOfEntries(self):
    return len(self.VLANTerminationList)

  def AddInterface(self, ifname, upstream, iftype):
    state = EthernetState(ifname, upstream, iftype)
    self._Interfaces[self._NextInterface] = state
    self._NextInterface += 1

  def GetInterface(self, ifnum):
    state = self._Interfaces[ifnum]
    return state.iftype(state)

  def IterInterfaces(self):
    for ifnum in sorted(self._Interfaces.keys()):
      interface = self.GetInterface(ifnum)
      yield ifnum, interface


def main():
  pass

if __name__ == '__main__':
  main()

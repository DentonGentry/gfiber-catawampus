#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-181 MoCA objects for Broadcom chipsets."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import pynetlinux
import tr.core
import tr.tr181_v2_2
import netdev


BASE181MOCA = tr.tr181_v2_2.Device_v2_2.Device.MoCA
PYNETIFCONF = pynetlinux.ifconfig.Interface


class BrcmMocaInterface(BASE181MOCA.Interface):
  """An implementation of tr181 Device.MoCA.Interface for Broadcom chipsets."""

  def __init__(self, ifname, upstream=False):
    BASE181MOCA.Interface.__init__(self)
    self.ifname = ifname
    self.Alias = ifname
    self.upstream = upstream
    self._pynet = PYNETIFCONF(ifname)

  @property
  def Name(self):
    return self.ifname

  @property
  def LowerLayers(self):
    # In theory this is writeable, but it is nonsensical to write to it.
    return ''

  @property
  def Upstream(self):
    return self.upstream

  @property
  def MACAddress(self):
    return self._pynet.get_mac()

  @property
  def Status(self):
    if not self._pynet.is_up():
      return 'Down'
    (speed, duplex, auto, link_up) = self._pynet.get_link_info()
    if link_up:
      return 'Up'
    else:
      return 'Dormant'


class BrcmMocaInterfaceStatsLinux26(BASE181MOCA.Interface.Stats):
  """tr181 Device.MoCA.Interface.Stats for Broadcom chipsets."""

  def __init__(self, ifname):
    BASE181MOCA.Interface.Stats.__init__(self)
    self._netdev = netdev.NetdevStatsLinux26(ifname)

  def __getattr__(self, name):
    if hasattr(self._netdev, name):
      return getattr(self._netdev, name)
    else:
      raise AttributeError


class BrcmMoca(BASE181MOCA):
  """An implementation of tr181 Device.MoCA for Broadcom chipsets."""

  def __init__(self):
    BASE181MOCA.__init__(self)
    self.InterfaceList = {}

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)


def main():
  pass

if __name__ == '__main__':
  main()

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

"""Implementation of tr-181 Device.Ethernet hierarchy of objects.

Handles the Device.Ethernet portion of TR-181, as described
in http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import pynetlinux
import tr.core
import tr.cwmpdate
import tr.tr181_v2_4
import tr.types
import tr.x_catawampus_tr181_2_0
import netdev

CATADEVICE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
CATAETHERNET = CATADEVICE.Device.Ethernet
PYNETIFCONF = pynetlinux.ifconfig.Interface


class EthernetInterfaceStatsLinux26(netdev.NetdevStatsLinux26,
                                    CATAETHERNET.Interface.Stats):
  """tr181 Ethernet.Interface.{i}.Stats implementation for Linux eth#."""

  def __init__(self, ifname, qfiles=None, numq=0, hipriq=0):
    netdev.NetdevStatsLinux26.__init__(self, ifname, qfiles, numq, hipriq)
    CATAETHERNET.Interface.Stats.__init__(self)
    if not qfiles:
      self.Unexport('X_CATAWAMPUS-ORG_DiscardFrameCnts')
      self.Unexport('X_CATAWAMPUS-ORG_DiscardPacketsReceivedHipri')


class EthernetInterfaceLinux26(CATAETHERNET.Interface):
  """Handling for a Linux 2.6-style device like eth0/eth1/etc.

  Args:
    ifname: netdev name, like 'eth0'
    qfiles: path to per-queue discard count files
    numq: number of per-queue discard files to look for
  """

  DuplexMode = tr.types.ReadOnlyString('Auto')
  Enable = tr.types.ReadOnlyBool(True)
  LowerLayers = tr.types.ReadOnlyString('')
  Name = tr.types.ReadOnlyString('')
  MaxBitRate = tr.types.ReadOnlyInt(-1)
  Upstream = tr.types.ReadOnlyBool(False)

  def __init__(self, ifname, upstream=False, qfiles=None, numq=0, hipriq=0):
    super(EthernetInterfaceLinux26, self).__init__()
    self._pynet = PYNETIFCONF(ifname)
    self._ifname = ifname
    self._qfiles = qfiles
    self._numq = numq
    self._hipriq = hipriq
    self.Unexport('Alias')
    type(self).Name.Set(self, ifname)
    type(self).Upstream.Set(self, upstream)

  @property
  def LastChange(self):
    return tr.cwmpdate.format(0)

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

  @property
  def Stats(self):
    return EthernetInterfaceStatsLinux26(
        ifname=self._ifname, qfiles=self._qfiles,
        numq=self._numq, hipriq=self._hipriq)

  @property
  def X_CATAWAMPUS_ORG_ActualBitRate(self):
    (speed, duplex, auto, link_up) = self._pynet.get_link_info()
    return speed

  @property
  def X_CATAWAMPUS_ORG_ActualDuplexMode(self):
    (speed, duplex, auto, link_up) = self._pynet.get_link_info()
    return 'Full' if duplex else 'Half'


def main():
  pass

if __name__ == '__main__':
  main()

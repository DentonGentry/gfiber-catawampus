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
import tr.cwmptypes
import tr.x_catawampus_tr181_2_0
import netdev

CATADEVICE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
CATAETHERNET = CATADEVICE.Device.Ethernet

# Unit tests can override these.
PYNETIFCONF = pynetlinux.ifconfig.Interface


class EthernetInterfaceStatsLinux26(netdev.NetdevStatsLinux26,
                                    CATAETHERNET.Interface.Stats):
  """tr181 Ethernet.Interface.{i}.Stats implementation for Linux eth#."""

  def __init__(self, ifname, qfiles=None, numq=0, hipriq=0):
    netdev.NetdevStatsLinux26.__init__(self, ifname, qfiles, numq, hipriq)
    CATAETHERNET.Interface.Stats.__init__(self)
    if not qfiles:
      self.Unexport(['X_CATAWAMPUS-ORG_DiscardFrameCnts',
                     'X_CATAWAMPUS-ORG_DiscardPacketsReceivedHipri'])


class EthernetInterfaceLinux26(CATAETHERNET.Interface):
  """Handling for a Linux 2.6-style device like eth0/eth1/etc.

  Args:
    ifname: netdev name, like 'eth0'
    upstream: True if this interface points to the WAN.
    qfiles: path to per-queue discard count files
    numq: number of per-queue discard files to look for
    hipriq: which queue number is high priority
    status_fcn: function to be called in Status method. If it
      returns a string, use it for Status instead of the builtin
      handling.
    maxbitrate: For interfaces where the bitrate can't be queried
      the value for MaxBitRate can be supplied.
  """

  Enable = tr.cwmptypes.ReadOnlyBool(True)
  LowerLayers = tr.cwmptypes.ReadOnlyString('')
  Name = tr.cwmptypes.ReadOnlyString('')
  Upstream = tr.cwmptypes.ReadOnlyBool(False)

  def __init__(self, ifname, upstream=False,
               qfiles=None, numq=0, hipriq=0,
               status_fcn=None, maxbitrate=0):
    super(EthernetInterfaceLinux26, self).__init__()
    self._pynet = PYNETIFCONF(ifname)
    self._ifname = ifname
    self._qfiles = qfiles
    self._numq = numq
    self._hipriq = hipriq
    self._status_fcn = status_fcn
    self._maxbitrate = maxbitrate
    self.Unexport(['Alias'])
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
    if self._status_fcn:
      s = self._status_fcn()
      if s: return s
    if not self._pynet.is_up():
      return 'Down'
    (_, _, _, link_up) = self._GetLinkInfo()
    if link_up is None:
      return 'Unknown'
    elif link_up:
      return 'Up'
    else:
      return 'Down'

  @property
  def Stats(self):
    return EthernetInterfaceStatsLinux26(
        ifname=self._ifname, qfiles=self._qfiles,
        numq=self._numq, hipriq=self._hipriq)

  @property
  def MaxBitRate(self):
    if self._maxbitrate:
      return self._maxbitrate
    (speed, _, _, _) = self._GetLinkInfo()
    return speed or 0  # follow the same convention as get_link_info(),
                       # in which 0 stands for "unknown".

  @property
  def DuplexMode(self):
    (_, duplex, _, _) = self._GetLinkInfo()
    if duplex is None:
      return 'Unknown'
    elif duplex:
      return 'Full'
    else:
      return 'Half'

  # Initially, we interpreted DuplexMode and MaxBitRate to read back
  # the configured settings. For example, they would return 'Auto'
  # and -1. We added the X_CATAWAMPUS_ORG_ActualBitRate and
  # X_CATAWAMPUS_ORG_ActualDuplexMode to provide the oper status.
  # We've decided to make DuplexMode and MaxBitRate reflect the
  # operational status after all, but retain these two for backwards
  # compatibility.
  @property
  def X_CATAWAMPUS_ORG_ActualBitRate(self):
    return self.MaxBitRate

  @property
  def X_CATAWAMPUS_ORG_ActualDuplexMode(self):
    return self.DuplexMode

  def _GetLinkInfo(self):
    """Call self._pynet.get_link_info() and handle any IOErrors.

    Returns:
       the same tuple as self._pynet.get_link_info(); if there's been
       an error, returns a bunch of Nones.
    """
    try:
      return self._pynet.get_link_info()
    except IOError:
      return (None, None, None, None)

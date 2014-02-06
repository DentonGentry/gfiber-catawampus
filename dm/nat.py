#!/usr/bin/python
# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Implementation of tr-181 Device.NAT hierarchy of objects.

Handles the Device.NAT portion of TR-181, as described
in http://www.broadband-forum.org/cwmp/tr-181-2-6-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import tr.mainloop
import tr.tr181_v2_6
import tr.types
import tr.x_catawampus_tr181_2_0

BASENAT = tr.tr181_v2_6.Device_v2_6.Device.NAT
RESTARTCMD = ['restart', 'firewall']


class NAT(BASENAT):
  """tr181 Device.NAT."""
  InterfaceSettingNumberOfEntries = tr.types.NumberOf()
  PortMappingNumberOfEntries = tr.types.NumberOf()

  def __init__(self, dmroot):
    super(NAT, self).__init__()
    self.dmroot = dmroot
    self.InterfaceSettingList = {}
    self.PortMappingList = {}
    type(self).InterfaceSettingNumberOfEntries.SetList(
        self, self.InterfaceSettingList)
    type(self).PortMappingNumberOfEntries.SetList(self, self.PortMappingList)

  def PortMapping(self):
    return PortMapping(parent=self)

  def GetIPInterface(self, ipif):
    """Return the Device.IP.Interface.{i} object in dmroot for ipif."""
    try:
      return self.dmroot.GetExport(ipif)
    except (AttributeError, KeyError):
      return None

  @tr.mainloop.WaitUntilIdle
  def WriteConfigs(self):
    """Write out configs for NAT."""
    config = []
    for p in self.PortMappingList.values():
      config.append(p.ConfigLine())
    # TODO(dgentry) decide on format of file


class PortMapping(BASENAT.PortMapping):
  """tr181 Device.NAT.Portmapping."""
  AllInterfaces = tr.types.TriggerBool(False)
  Description = tr.types.String()
  Enable = tr.types.TriggerBool(False)
  ExternalPort = tr.types.TriggerUnsigned(0)
  ExternalPortEndRange = tr.types.TriggerUnsigned(0)
  InternalClient = tr.types.TriggerString()
  InternalPort = tr.types.TriggerUnsigned(0)
  LeaseDuration = tr.types.TriggerUnsigned(0)
  Protocol = tr.types.TriggerString()
  RemoteHost = tr.types.TriggerIP4Addr()

  def __init__(self, parent):
    super(PortMapping, self).__init__()
    self.parent = parent
    self.interface = ''
    self.Unexport(['Alias'])

  def GetInterface(self):
    """Return the Interface if it exists, or an empty string if it doesn't.

    tr-181 says: "If the referenced object is deleted, the parameter value
    MUST be set to an empty string."

    Returns:
      the Device.IP.Interface if it exists, or an empty string if it doesn't.
    """
    if self.parent.GetIPInterface(self.interface) is None:
      return ''
    return self.interface

  def SetInterface(self, value):
    if self.parent.GetIPInterface(value) is None:
      raise ValueError('No such Device.IP.Interface')
    self.interface = value
    self.Triggered()

  Interface = property(GetInterface, SetInterface, None,
                       'Device.NAT.PortMapping.Interface')

  @LeaseDuration.validator
  def LeaseDuration(self, value):
    if int(value) != 0:
      raise ValueError('Dynamic PortMapping is not supported.')
    return int(value)

  def _IsComplete(self):
    """Returns True if object is fully configured for Linux iptables."""
    if not self.InternalPort or not self.InternalClient or not self.Protocol:
      return False
    if not self.AllInterfaces and not self.Interface:
      return False
    return True

  @property
  def Status(self):
    if not self.Enable:
      return 'Disabled'
    if not self._IsComplete():
      return 'Error_Misconfigured'
    return 'Enabled'

  def Triggered(self):
    self.parent.WriteConfigs()

  def ConfigLine(self):
    """Return the configuration line for update-acs-iptables."""

    if not self._IsComplete():
      return None
    proto = self.Protocol
    src = '0/0' if not self.RemoteHost else self.RemoteHost
    if self.AllInterfaces:
      gw = '0/0'
    else:
      ip = self.parent.GetIPInterface(self.interface)
      if not ip or not ip.IPv4AddressList:
        return None
      key = ip.IPv4AddressList.keys()[0]
      gw = ip.IPv4AddressList[key]
    dst = self.InternalClient
    # TODO(dgentry) ExternalPort=0 should become a dmzhost instead
    if self.ExternalPortEndRange:
      sport = '%d:%d' % (self.ExternalPort, self.ExternalPortEndRange)
    else:
      sport = '%d' % self.ExternalPort
    dport = self.InternalPort
    enb = 1 if self.Enable else 0
    return '%s %s %s %s %s %d %d' % (proto, src, gw, dst, sport, dport, enb)

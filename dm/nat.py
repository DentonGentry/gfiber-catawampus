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

import binascii
import socket
import subprocess
import traceback
import tr.helpers
import tr.mainloop
import tr.tr181_v2_6
import tr.cwmptypes
import tr.x_catawampus_tr181_2_0

BASENAT = tr.tr181_v2_6.Device_v2_6.Device.NAT
CATANAT = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.Device.NAT
DMZFILE4 = '/tmp/acs/dmzhostv4'
DMZFILE6 = '/tmp/acs/dmzhostv6'
OUTPUTFILE4 = '/tmp/cwmp_iptables'
OUTPUTFILE6 = '/tmp/cwmp_ip6tables'
RESTARTCMD = ['update-acs-iptables']


class NAT(BASENAT):
  """tr181 Device.NAT."""
  InterfaceSettingNumberOfEntries = tr.cwmptypes.NumberOf('InterfaceSettingList')
  PortMappingNumberOfEntries = tr.cwmptypes.NumberOf('PortMappingList')

  def __init__(self, dmroot):
    super(NAT, self).__init__()
    self.dmroot = dmroot
    self.InterfaceSettingList = {}
    self.PortMappingList = {}

  def PortMapping(self):
    return PortMapping(parent=self)

  def GetIPInterface(self, ipif):
    """Return the Device.IP.Interface.{i} object in dmroot for ipif."""
    try:
      return self.dmroot.GetExport(ipif)
    except (AttributeError, KeyError):
      return None

  def _PrefixLines(self, lines, outidx):
    """Return prefixed lines.
    Args
      lines: an array of lines of text
      outidx: the index to prefix
    Returns a string."""

    if not lines:
      return ''
    prefix = 'CWMP_%d_' % outidx
    prefixed = [prefix + x for x in lines]
    return '\n'.join(prefixed) + '\n\n'

  @tr.mainloop.WaitUntilIdle
  def WriteConfigs(self):
    """Write out configs for NAT.

    tr-181 Device.NAT.PortMapping.{i} provides four levels of precedence
    to be used if multiple portmappings could match a packet. We handle
    this by creating four lists of config file lines, and then outputting
    them in priority order.

    An "IDX_#" string in the COMMENT line lets us reconstruct the object
    numbering when read back in.
    """
    ip4configs = {}
    ip6configs = {}
    for i in range(1, 5):
      ip4configs[i] = []
      ip6configs[i] = []
      dmz4 = ''
      dmz6 = ''
    for (idx, mapping) in self.PortMappingList.iteritems():
      precedence = mapping.Precedence()
      ip4configs[precedence].append(mapping.ConfigLinesIP4(idx=idx))
      ip6configs[precedence].append(mapping.ConfigLinesIP6(idx=idx))
      if mapping.DmzIP4():
        dmz4 = mapping.DmzIP4()
      if mapping.DmzIP6():
        dmz6 = mapping.DmzIP6()
    outidx = 1
    try:
      with tr.helpers.AtomicFile(OUTPUTFILE4) as f:
        for i in range(1, 5):
          for lines in ip4configs[i]:
            if lines:
              f.write(self._PrefixLines(lines=lines, outidx=outidx))
              outidx += 1
      with tr.helpers.AtomicFile(OUTPUTFILE6) as f:
        for i in range(1, 5):
          for lines in ip6configs[i]:
            if lines:
              f.write(self._PrefixLines(lines=lines, outidx=outidx))
              outidx += 1
      if dmz4:
        with tr.helpers.AtomicFile(DMZFILE4) as f:
          f.write(dmz4)
      else:
        tr.helpers.Unlink(DMZFILE4)
      if dmz6:
        with tr.helpers.AtomicFile(DMZFILE6) as f:
          f.write(dmz6)
      else:
        tr.helpers.Unlink(DMZFILE6)
      subprocess.check_call(RESTARTCMD)
    except (IOError, OSError, subprocess.CalledProcessError):
      print 'Unable to update NAT\n'
      traceback.print_exc()


class PortMapping(CATANAT.PortMapping):
  """tr181 Device.NAT.Portmapping."""
  AllInterfaces = tr.cwmptypes.TriggerBool(False)
  Description = tr.cwmptypes.TriggerString('')
  Enable = tr.cwmptypes.TriggerBool(False)
  ExternalPort = tr.cwmptypes.TriggerUnsigned(0)
  ExternalPortEndRange = tr.cwmptypes.TriggerUnsigned(0)
  InternalClient = tr.cwmptypes.TriggerString()
  InternalPort = tr.cwmptypes.TriggerUnsigned(0)
  LeaseDuration = tr.cwmptypes.TriggerUnsigned(0)
  Protocol = tr.cwmptypes.TriggerString()
  RemoteHost = tr.cwmptypes.TriggerIP4Addr()
  X_CATAWAMPUS_ORG_PortRangeSize = tr.cwmptypes.TriggerUnsigned(0)

  def __init__(self, parent):
    super(PortMapping, self).__init__()
    self.parent = parent
    self.interface = ''
    self.Unexport(['Alias'])

  @Description.validator
  def Description(self, value):
    if len(str(value)) > 256:
      raise ValueError('Description length must be < 256 characters.')
    return str(value)

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

  def _IsDmzComplete(self):
    """Returns true if object is fully configured for DMZ operation."""
    return self.InternalClient and self.InternalPort == 0 and self.ExternalPort == 0

  def _IsNatComplete(self):
    """Returns True if object is fully configured for Linux iptables."""
    if not self.InternalPort or not self.InternalClient or not self.Protocol:
      return False
    if not self.AllInterfaces and not self.Interface:
      return False
    return True

  def Precedence(self):
    """Precedence to pick the winner when multiple rules match.

    tr-181 Device.NAT.PortMapping.{i} says:
    When wildcard values are used for RemoteHost and/or ExternalPort, the
    following precedence order applies (with the highest precedence listed
    first):

      1. Explicit RemoteHost, explicit ExternalPort
      2. Explicit RemoteHost, zero ExternalPort
      3. Empty RemoteHost, explicit ExternalPort
      4. Empty RemoteHost, zero ExternalPort
    If an incoming packet matches the criteria associated with more than one
    entry in this table, the CPE MUST apply the port mapping associated with
    the highest precedence entry.

    Returns: the precedence, an integer from 1 to 4.
    """
    if self.RemoteHost and self.ExternalPort:
      return 1
    elif self.RemoteHost:
      return 2
    elif self.ExternalPort:
      return 3
    else:
      return 4

  @property
  def Status(self):
    if not self.Enable:
      return 'Disabled'
    if not self._IsNatComplete() and not self._IsDmzComplete():
      return 'Error_Misconfigured'
    return 'Enabled'

  def Close(self):
    """Called by core.py:DeleteExportObjects()."""
    self.Triggered()

  def Triggered(self):
    self.parent.WriteConfigs()

  def _CommonConfigLines(self, idx):
    """Add configuration with identical handling for IPv4 and IPv6."""
    encoded = binascii.hexlify(self.Description)
    lines = ['COMMENT=IDX_%s:%s' % (str(idx), encoded)]
    lines.append('PROTOCOL=' + self.Protocol)

    lines.append('DEST=' + self.InternalClient)
    # TODO(dgentry) ExternalPort=0 should become a dmzhost instead
    if self.X_CATAWAMPUS_ORG_PortRangeSize:
      end = self.ExternalPort + self.X_CATAWAMPUS_ORG_PortRangeSize - 1
      sport = '%d:%d' % (self.ExternalPort, end)
    elif self.ExternalPortEndRange:
      sport = '%d:%d' % (self.ExternalPort, self.ExternalPortEndRange)
    else:
      sport = '%d' % self.ExternalPort
    lines.append('SPORT=' + sport)
    if self.X_CATAWAMPUS_ORG_PortRangeSize:
      end = self.InternalPort + self.X_CATAWAMPUS_ORG_PortRangeSize - 1
      dport = '%d:%d' % (self.InternalPort, end)
    else:
      dport = '%d' % self.InternalPort
    lines.append('DPORT=' + dport)
    lines.append('ENABLE=%d' % (self.Enable == True))

    return lines

  def ConfigLinesIP4(self, idx):
    """Return the configuration lines for update-acs-iptables IP4 rules.

    Args:
      idx: the {i} in Device.NAT.PortMapping.{i}

    Returns:
      a list of text lines for update-acs-iptables
    """

    if not self._IsNatComplete() or not self.Enable:
      return []
    if self.InternalClient and tr.helpers.IsIP6Addr(self.InternalClient):
      return []
    if self.RemoteHost and tr.helpers.IsIP6Addr(self.RemoteHost):
      return []

    lines = self._CommonConfigLines(idx=idx)
    src = '0/0' if not self.RemoteHost else self.RemoteHost
    lines.append('SOURCE=%s' % src)
    if self.AllInterfaces:
      gw = '0/0'
    else:
      ip = self.parent.GetIPInterface(self.interface)
      if not ip or not ip.IPv4AddressList:
        return []
      key = ip.IPv4AddressList.keys()[0]
      gw = ip.IPv4AddressList[key].IPAddress
    lines.append('GATEWAY=%s' % gw)
    return lines

  def ConfigLinesIP6(self, idx):
    """Return the configuration lines for update-acs-iptables IP6 rules.

    Args:
      idx: the {i} in Device.NAT.PortMapping.{i}

    Returns:
      a list of text lines for update-acs-iptables
    """

    if not self._IsNatComplete() or not self.Enable:
      return []
    if self.InternalClient and tr.helpers.IsIP4Addr(self.InternalClient):
      return []
    if self.RemoteHost and tr.helpers.IsIP4Addr(self.RemoteHost):
      return []

    lines = self._CommonConfigLines(idx=idx)
    src = '::/0' if not self.RemoteHost else self.RemoteHost
    lines.append('SOURCE=%s' % src)
    if self.AllInterfaces:
      gw = '::/0'
    else:
      ip = self.parent.GetIPInterface(self.interface)
      if not ip or not ip.IPv6AddressList:
        return []
      key = ip.IPv6AddressList.keys()[0]
      gw = ip.IPv6AddressList[key].IPAddress
    lines.append('GATEWAY=%s' % gw)
    return lines

  def DmzIP4(self):
    if not self._IsDmzComplete() or not self.Enable:
      return None
    if self.InternalClient and tr.helpers.IsIP6Addr(self.InternalClient):
      return None
    return self.InternalClient

  def DmzIP6(self):
    if not self._IsDmzComplete() or not self.Enable:
      return None
    if self.InternalClient and tr.helpers.IsIP4Addr(self.InternalClient):
      return None
    return self.InternalClient

#!/usr/bin/python
# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Implementation of tr-181 Device.IP.Interface hierarchy of objects.

Handles the Device.IP.Interface portion of TR-181, as described
in http://www.broadband-forum.org/cwmp/tr-181-2-6-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import netdev
import pynetlinux
import socket
import tr.core
import tr.cwmpdate
import tr.tr181_v2_6
import tr.types

try:
  import netifaces
  IFADDRESSES = netifaces.ifaddresses
except ImportError:
  print 'Skipping netifaces module for unit test'
  IFADDRESSES = None

BASEIPINTF = tr.tr181_v2_6.Device_v2_6.Device.IP.Interface
PYNETIFCONF = pynetlinux.ifconfig.Interface


class IPInterfaceStatsLinux26(netdev.NetdevStatsLinux26, BASEIPINTF.Stats):
  """tr181 IP.Interface.{i}.Stats implementation for Linux eth#."""

  def __init__(self, ifname):
    netdev.NetdevStatsLinux26.__init__(self, ifname)
    BASEIPINTF.Stats.__init__(self)


class IPInterfaceLinux26(BASEIPINTF):
  """Handling for a Linux 2.6-style device like eth0/eth1/etc.

  Args:
    ifname: netdev name, like 'eth0'
    lowerlayers: string path of Device.{Ethernet,MoCA,etc}
  """

  Enable = tr.types.ReadOnlyBool(True)
  IPv4Enable = tr.types.ReadOnlyBool(True)
  IPv6Enable = tr.types.ReadOnlyBool(True)
  LowerLayers = tr.types.ReadOnlyString('')
  Name = tr.types.ReadOnlyString('')
  Type = tr.types.ReadOnlyString('Normal')

  def __init__(self, ifname, lowerlayers=''):
    super(IPInterfaceLinux26, self).__init__()
    self._pynet = PYNETIFCONF(ifname)
    self._ifname = ifname
    self.Unexport('Alias')
    self.Unexport('AutoIPEnable')
    self.Unexport('Router')
    self.Unexport('Loopback')
    self.Unexport('Reset')
    self.Unexport('ULAEnable')
    type(self).Name.Set(self, ifname)
    type(self).LowerLayers.Set(self, lowerlayers)
    self.IPv6PrefixList = {}
    if IFADDRESSES is not None:
      self.IPv4AddressList = tr.core.AutoDict(
          'IPv4AddressList', iteritems=self.IterIPv4Addresses,
          getitem=self.GetIPv4AddressByIndex)
      self.IPv6AddressList = tr.core.AutoDict(
          'IPv6AddressList', iteritems=self.IterIPv6Addresses,
          getitem=self.GetIPv6AddressByIndex)
    else:
      self.IPv4AddressList = {}
      self.IPv6AddressList = {}

  @property
  def LastChange(self):
    return tr.cwmpdate.format(0)

  @property
  def MaxMTUSize(self):
    return self._pynet.get_mtu()

  @property
  def Stats(self):
    return IPInterfaceStatsLinux26(ifname=self._ifname)

  @property
  def Status(self):
    return 'Up' if self._pynet.is_up() else 'LowerLayerDown'

  @property
  def IPv4AddressNumberOfEntries(self):
    return len(self.IPv4AddressList)

  @property
  def IPv6AddressNumberOfEntries(self):
    return len(self.IPv6AddressList)

  @property
  def IPv6PrefixNumberOfEntries(self):
    return len(self.IPv6PrefixList)

  def GetIpv4Address(self, ipdict):
    ipaddr = ipdict.get('addr', '0.0.0.0')
    netmask = ipdict.get('netmask', '0.0.0.0')
    return IPv4AddressLinux26(ipaddr=ipaddr, netmask=netmask)

  def IterIPv4Addresses(self):
    """Retrieves a list of all IP addresses for this interface."""
    ips = IFADDRESSES(self._ifname)
    ip4s = ips.get(socket.AF_INET, [])
    for idx, ipdict in enumerate(ip4s):
      yield idx, self.GetIpv4Address(ipdict=ipdict)

  def GetIPv4AddressByIndex(self, index):
    ips = IFADDRESSES(self._ifname)
    ip4s = ips.get(socket.AF_INET, [])
    if index >= len(ip4s):
      raise IndexError('No such object IPv4Address.{0}'.format(index))
    return self.GetIpv4Address(ipdict=ip4s[index])

  def GetIpv6Address(self, ipdict):
    ipaddr = ipdict.get('addr', '0.0.0.0')
    return IPv6AddressLinux26(ipaddr=ipaddr)

  def IterIPv6Addresses(self):
    """Retrieves a list of all IP addresses for this interface."""
    ips = IFADDRESSES(self._ifname)
    ip6s = ips.get(socket.AF_INET6, [])
    for idx, ipdict in enumerate(ip6s):
      yield idx, self.GetIpv6Address(ipdict=ipdict)

  def GetIPv6AddressByIndex(self, index):
    ips = IFADDRESSES(self._ifname)
    ip6s = ips.get(socket.AF_INET6, [])
    if index >= len(ip6s):
      raise IndexError('No such object IPv6Address.{0}'.format(index))
    return self.GetIpv6Address(ipdict=ip6s[index])


class IPv4AddressLinux26(BASEIPINTF.IPv4Address):
  """tr181 Device.IP.Interface.{i}.IPv4Address implementation for Linux."""
  Enable = tr.types.ReadOnlyBool(True)
  IPAddress = tr.types.ReadOnlyString('')
  Status = tr.types.ReadOnlyString('Enabled')
  SubnetMask = tr.types.ReadOnlyString('')

  def __init__(self, ipaddr, netmask):
    super(IPv4AddressLinux26, self).__init__()
    self.Unexport('AddressingType')
    self.Unexport('Alias')
    type(self).IPAddress.Set(self, ipaddr)
    type(self).SubnetMask.Set(self, netmask)


class IPv6AddressLinux26(BASEIPINTF.IPv6Address):
  """tr181 Device.IP.Interface.{i}.IPv6Address implementation for Linux."""
  Enable = tr.types.ReadOnlyBool(True)
  IPAddress = tr.types.ReadOnlyString('')
  IPAddressStatus = tr.types.ReadOnlyString('Preferred')
  Status = tr.types.ReadOnlyString('Enabled')

  def __init__(self, ipaddr):
    super(IPv6AddressLinux26, self).__init__()
    self.Unexport('Alias')
    self.Unexport('Anycast')
    self.Unexport('Origin')
    self.Unexport('PreferredLifetime')
    self.Unexport('Prefix')
    self.Unexport('ValidLifetime')
    type(self).IPAddress.Set(self, ipaddr)

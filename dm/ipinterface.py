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
import struct
import subprocess
import traceback
import tr.core
import tr.cwmpdate
import tr.mainloop
import tr.session
import tr.tr181_v2_6
import tr.types
import tr.x_catawampus_tr181_2_0

try:
  import netifaces
  IFADDRESSES = netifaces.ifaddresses
except ImportError:
  print 'Skipping netifaces module for unit test'
  IFADDRESSES = None

BASEIPINTF = tr.tr181_v2_6.Device_v2_6.Device.IP.Interface
CATA181IP = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.Device.IP
IPCONFIG = ['tr69_ipconfig']
PYNETIFCONF = pynetlinux.ifconfig.Interface


def _ConvertMaskToCIDR(mask):
  """Convert a netmask like 255.255.255.0 to a CIDR length like /24."""
  bits = int(struct.unpack('!I',socket.inet_aton(mask))[0])
  found_one_bit = False
  maskbits = 0
  for i in range(32):
    if (bits >> i) & 1 == 1:
      found_one_bit = True
    elif found_one_bit:
      return -1
    else:
      maskbits += 1
  return 32 - maskbits


class IPInterfaceStatsLinux26(netdev.NetdevStatsLinux26, BASEIPINTF.Stats):
  """tr181 IP.Interface.{i}.Stats implementation for Linux eth#."""

  def __init__(self, ifname):
    netdev.NetdevStatsLinux26.__init__(self, ifname)
    BASEIPINTF.Stats.__init__(self)


class IPInterfaceLinux26(CATA181IP.Interface):
  """Handling for a Linux 2.6-style device like eth0/eth1/etc.

  Args:
    ifname: netdev name, like 'eth0'
    lowerlayers: string path of Device.{Ethernet,MoCA,etc}
  """

  Enable = tr.types.ReadOnlyBool(True)
  IPv4Enable = tr.types.ReadOnlyBool(True)
  IPv4AddressNumberOfEntries = tr.types.NumberOf('IPv4AddressList')
  IPv6AddressNumberOfEntries = tr.types.NumberOf('IPv6AddressList')
  IPv6PrefixNumberOfEntries = tr.types.NumberOf('IPv6PrefixList')
  IPv6Enable = tr.types.ReadOnlyBool(True)
  LowerLayers = tr.types.ReadOnlyString('')
  Name = tr.types.ReadOnlyString('')
  Type = tr.types.ReadOnlyString('Normal')

  def __init__(self, ifname, lowerlayers=''):
    super(IPInterfaceLinux26, self).__init__()
    self._pynet = PYNETIFCONF(ifname)
    self._ifname = ifname
    self.Unexport(['Alias', 'AutoIPEnable', 'Router', 'Loopback', 'Reset',
                   'ULAEnable'])
    type(self).Name.Set(self, ifname)
    type(self).LowerLayers.Set(self, lowerlayers)
    self.IPv4AddressList = self._PopulateIPv4AddressList()
    self.IPv6AddressList = self._PopulateIPv6AddressList()
    self.IPv6PrefixList = {}

  def IPv4Address(self):
    return IPv4AddressLinux26(parent=self)

  def IPv6Address(self):
    return IPv6AddressLinux26(parent=self)

  @property
  def X_CATAWAMPUS_ORG_IP4Address(self):
    ip4 = self.IPv4AddressList.values()
    if ip4:
      return ip4[0].IPAddress
    return ''

  @property
  def X_CATAWAMPUS_ORG_IP6Address(self):
    ip6 = self.IPv6AddressList.values()
    if ip6:
      return ip6[0].IPAddress
    return ''

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

  @tr.mainloop.WaitUntilIdle
  def UpdateConfig(self):
    """Pass IP addresses to the platform."""
    cmd = IPCONFIG + [self._ifname]
    for addr in self.IPv4AddressList.values():
      ip = addr.IPAddress if addr.IPAddress else ''
      mask = _ConvertMaskToCIDR(addr.SubnetMask) if addr.SubnetMask else 0
      if ip and mask:
        cmd.append('%s/%d' % (ip, mask))
    try:
      subprocess.check_call(cmd)
    except (IOError, OSError, subprocess.CalledProcessError):
      print 'Unable to execute %s\n' % cmd
      traceback.print_exc()

  def _PopulateIPv4AddressList(self):
    """Device.IP.Interface.{i}.IPv4Address.{i}."""
    ips = IFADDRESSES(self._ifname)
    ip4s = ips.get(socket.AF_INET, [])
    result = {}
    for idx, ipdict in enumerate(ip4s, start=1):
      ip4 = ipdict.get('addr', '0.0.0.0')
      mask = ipdict.get('netmask', '0.0.0.0')
      ipa = IPv4AddressLinux26(parent=self, ipaddr=ip4, netmask=mask)
      result[str(idx)] = ipa
    return result

  def _PopulateIPv6AddressList(self):
    """Device.IP.Interface.{i}.IPv6Address.{i}."""
    ips = IFADDRESSES(self._ifname)
    ip6s = ips.get(socket.AF_INET6, [])
    result = {}
    for idx, ipdict in enumerate(ip6s, start=1):
      ip6 = ipdict.get('addr', '::0')
      # Handle Link Local addresses 'fe80::fa8f:caff:fe00:24a4%lan0'
      ip6 = ip6.split('%')[0]
      ipa = IPv6AddressLinux26(parent=self, ipaddr=ip6)
      result[str(idx)] = ipa
    return result


class IPv4AddressLinux26(BASEIPINTF.IPv4Address):
  """tr181 Device.IP.Interface.{i}.IPv4Address implementation for Linux."""
  Enable = tr.types.ReadOnlyBool(True)
  IPAddress = tr.types.TriggerIP4Addr('')
  Status = tr.types.ReadOnlyString('Enabled')
  SubnetMask = tr.types.TriggerIP4Addr('')

  def __init__(self, parent, ipaddr='', netmask=''):
    super(IPv4AddressLinux26, self).__init__()
    self.Unexport(['AddressingType', 'Alias'])
    self._initialized = False
    self._parent = parent
    self.IPAddress = ipaddr
    self.SubnetMask = netmask
    self._initialized = True

  def Triggered(self):
    """Called when parameters are modified.

    We ignore changes which occur while the object is initializing.
    """
    if self._initialized:
      self._parent.UpdateConfig()


class IPv6AddressLinux26(BASEIPINTF.IPv6Address):
  """tr181 Device.IP.Interface.{i}.IPv6Address implementation for Linux."""
  Enable = tr.types.ReadOnlyBool(True)
  IPAddress = tr.types.ReadOnlyIP6Addr('')
  IPAddressStatus = tr.types.ReadOnlyString('Preferred')
  Status = tr.types.ReadOnlyString('Enabled')

  def __init__(self, parent, ipaddr=''):
    super(IPv6AddressLinux26, self).__init__()
    self.Unexport(['Alias', 'Anycast', 'Origin', 'PreferredLifetime',
                   'Prefix', 'ValidLifetime'])
    self._parent = parent
    type(self).IPAddress.Set(self, ipaddr)

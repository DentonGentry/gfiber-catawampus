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
# pylint:disable=invalid-name

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
import tr.basemodel
import tr.cwmpdate
import tr.mainloop
import tr.session
import tr.cwmptypes
import tr.x_catawampus_tr181_2_0

try:
  import netifaces  # pylint:disable=g-import-not-at-top
  IFADDRESSES = netifaces.ifaddresses
except ImportError:
  print 'Skipping netifaces module for unit test'
  IFADDRESSES = None

BASEIPINTF = tr.basemodel.Device.IP.Interface
CATA181IP = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.Device.IP
IPCONFIG = ['tr69_ipconfig']
PYNETIFCONF = pynetlinux.ifconfig.Interface


def _ConvertMaskToCIDR(mask):
  """Convert a netmask like 255.255.255.0 to a CIDR length like /24."""
  bits = int(struct.unpack('!I', socket.inet_pton(socket.AF_INET, mask))[0])
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

  Enable = tr.cwmptypes.ReadOnlyBool(True)
  IPv4Enable = tr.cwmptypes.ReadOnlyBool(True)
  IPv4AddressNumberOfEntries = tr.cwmptypes.NumberOf('IPv4AddressList')
  IPv6AddressNumberOfEntries = tr.cwmptypes.NumberOf('IPv6AddressList')
  IPv6PrefixNumberOfEntries = tr.cwmptypes.NumberOf('IPv6PrefixList')
  IPv6Enable = tr.cwmptypes.ReadOnlyBool(True)
  LowerLayers = tr.cwmptypes.ReadOnlyString('')
  Name = tr.cwmptypes.ReadOnlyString('')
  Type = tr.cwmptypes.ReadOnlyString('Normal')

  def __init__(self, ifname, lowerlayers=''):
    super(IPInterfaceLinux26, self).__init__()
    self._pynet = PYNETIFCONF(ifname)
    self._ifname = ifname
    self.Unexport(['Alias', 'AutoIPEnable', 'Router', 'Loopback', 'Reset',
                   'ULAEnable'])
    type(self).Name.Set(self, ifname)
    type(self).LowerLayers.Set(self, lowerlayers)
    self.IPv6PrefixList = {}
    self._Stats = IPInterfaceStatsLinux26(ifname=ifname)

  def IPv4Address(self):
    return IPv4Address(parent=self, origin='Static')

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
    return self._Stats

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

  @property
  @tr.session.cache
  def IPv4AddressList(self):
    """Device.IP.Interface.{i}.IPv4Address.{i}."""
    ips = IFADDRESSES(self._ifname)
    ip4s = sorted(ips.get(socket.AF_INET, []))
    result = {}
    for idx, ipdict in enumerate(ip4s, start=1):
      ip4 = ipdict.get('addr', '0.0.0.0')
      mask = ipdict.get('netmask', '0.0.0.0')
      ipa = IPv4Address(parent=self, ipaddr=ip4, netmask=mask)
      result[str(idx)] = ipa
    return result

  @property
  @tr.session.cache
  def IPv6AddressList(self):
    """Device.IP.Interface.{i}.IPv6Address.{i}."""
    ips = IFADDRESSES(self._ifname)
    ip6s = sorted(ips.get(socket.AF_INET6, []))
    result = {}
    for idx, ipdict in enumerate(ip6s, start=1):
      ip6 = ipdict.get('addr', '::0')
      ipa = IPv6Address(parent=self, ipaddr=ip6)
      result[str(idx)] = ipa
    return result


class IPv4Address(BASEIPINTF.IPv4Address):
  """tr181 Device.IP.Interface.{i}.IPv4Address implementation for Linux."""
  AddressingType = tr.cwmptypes.ReadOnlyEnum(['DHCP', 'IKEv2', 'AutoIP',
                                              'IPCP', 'Static', 'Unknown'],
                                             'Unknown')
  Enable = tr.cwmptypes.ReadOnlyBool(True)
  IPAddress = tr.cwmptypes.TriggerIP4Addr('')
  Status = tr.cwmptypes.ReadOnlyString('Enabled')
  SubnetMask = tr.cwmptypes.TriggerIP4Addr('')

  def __init__(self, parent, ipaddr='', netmask='', origin=None):
    super(IPv4Address, self).__init__()
    self.Unexport(['Alias'])
    self._initialized = False
    self._parent = parent
    self.IPAddress = ipaddr
    self.SubnetMask = netmask
    if origin:
      type(self).AddressingType.Set(self, origin)
    self._initialized = True

  def Triggered(self):
    """Called when parameters are modified.

    We ignore changes which occur while the object is initializing.
    """
    if self._initialized:
      self._parent.UpdateConfig()


class IPv6Address(BASEIPINTF.IPv6Address):
  """tr181 Device.IP.Interface.{i}.IPv6Address implementation for Linux."""
  Enable = tr.cwmptypes.ReadOnlyBool(True)
  IPAddress = tr.cwmptypes.ReadOnlyIP6Addr('')
  IPAddressStatus = tr.cwmptypes.ReadOnlyString('Preferred')
  Origin = tr.cwmptypes.ReadOnlyEnum(['AutoConfigured', 'DHCPv6', 'IKEv2',
                                      'WellKnown', 'Static', 'Unknown'],
                                     'Unknown')
  Status = tr.cwmptypes.ReadOnlyString('Enabled')

  def __init__(self, parent, ipaddr='', origin='Unknown'):
    super(IPv6Address, self).__init__()
    self.Unexport(['Alias', 'Anycast', 'PreferredLifetime',
                   'Prefix', 'ValidLifetime'])
    self._parent = parent
    if '%' in ipaddr:
      # Handle Link Local addresses 'fe80::fa8f:caff:fe00:24a4%lan0'
      ipaddr = ipaddr.split('%')[0]
      origin = 'AutoConfigured'
    type(self).IPAddress.Set(self, ipaddr)
    type(self).Origin.Set(self, origin)

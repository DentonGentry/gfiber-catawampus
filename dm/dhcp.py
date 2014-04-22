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

# unittest requires method names starting in 'test'
# pylint: disable-msg=C6409

"""TR-181 Device.DHCPv[46] implementation for dnsmasq.

Provides a way to configure the DHCP server via the ACS.
The Device.DHCPv[46].Server data models are translated into
a configuration file for dnsmasq.

    # saved by catawampus 2013-12-01 16:26:47.425170
    dhcp-range=1.1.1.1,2.2.2.2,86400
    domain=example.com
    dhcp-option=option:router,9.9.9.9
    dhcp-option=option:ntp-server,5.5.5.5,6.6.6.6
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
import tr.tr181_v2_6
import tr.types


# DHCP Option values
CL = 61  # ClientID
HN = 12  # HostName
UC = 77  # UserClassID
VC = 60  # VendorClassID


DHCP4SERVERPOOL = tr.tr181_v2_6.Device_v2_6.Device.DHCPv4.Server.Pool


class Client(DHCP4SERVERPOOL.Client):
  """tr-181 Device.DHCPv4.Server.{i}.Client.{i}."""
  Active = tr.types.ReadOnlyBool(True)
  Chaddr = tr.types.ReadOnlyMacAddr('')
  IPv4AddressNumberOfEntries = tr.types.NumberOf('IPv4AddressList')
  OptionNumberOfEntries = tr.types.NumberOf('OptionList')

  def __init__(self, chaddr, ipaddr, expiry=0,
               clientid=None, hostname=None, userclassid=None,
               vendorclassid=None):
    """tr-181 Device.DHCPv4.Server.{i}.Client.{i}.

    Args:
      ipaddr: a dotted-quad IP address.
      expiry: an integer number of seconds since the epoch UTC
        when the lease will expire, OR a string timestamp, OR
        a datetime object.
      clientid: DHCP ClientID from the client, if any.
      hostname: DHCP HostName from the client, if any.
      userclassid: UserClassID from the client, if any.
      vendorclassid: VendorClassID from the client, if any.
    """
    super(Client, self).__init__()
    self.Unexport(['Alias'])
    type(self).Chaddr.Set(self, chaddr)
    self.IPv4AddressList = {
        '1': ClientIPv4Address(ip=ipaddr, expiry=expiry),
    }
    self.next_ipv4 = 2
    self.OptionList = {}
    if clientid:
      self.OptionList['1'] = ClientOption(tag=CL, value=clientid)
    if hostname:
      self.OptionList['2'] = ClientOption(tag=HN, value=hostname)
    if userclassid:
      self.OptionList['3'] = ClientOption(tag=UC, value=userclassid)
    if vendorclassid:
      self.OptionList['4'] = ClientOption(tag=VC, value=vendorclassid)

  def AddIP(self, ipaddr, expiry=0):
    """Add a ClientIPv4Address."""
    c = ClientIPv4Address(ip=ipaddr, expiry=expiry)
    self.IPv4AddressList[str(self.next_ipv4)] = c
    self.next_ipv4 += 1


class ClientIPv4Address(DHCP4SERVERPOOL.Client.IPv4Address):
  IPAddress = tr.types.ReadOnlyIP4Addr('')
  LeaseTimeRemaining = tr.types.ReadOnlyDate(0)

  def __init__(self, ip, expiry):
    """tr-181 Device.DHCPv4.Server.{i}.Client.{i}.IPv4Address.{i}.

    Args:
      ip: IPv4 address in dotted quad notation
      expiry: integer time_t when the lease expires
    """
    super(ClientIPv4Address, self).__init__()
    type(self).IPAddress.Set(self, ip)
    type(self).LeaseTimeRemaining.Set(self, expiry)


class ClientOption(DHCP4SERVERPOOL.Client.Option):
  Tag = tr.types.ReadOnlyInt()
  Value = tr.types.ReadOnlyString()

  def __init__(self, tag, value):
    """tr-181 Device.DHCPv4.Server.{i}.Client.{i}.Option.{i}.
    Args:
      tag: numeric DHCP option tag
      value: string value
    """
    super(ClientOption, self).__init__()
    type(self).Tag.Set(self, tag)
    type(self).Value.Set(self, value)

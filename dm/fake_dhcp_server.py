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
# pylint:disable=invalid-name

"""TR-181 Device.DHCPv[46] implementation for FakeCPE.

Provides a way to configure the DHCP server via the ACS.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import time

import dhcp
import tr.tr181_v2_6
import tr.cwmptypes
import tr.x_catawampus_tr181_2_0

CATA181DEV = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
DHCP4SERVER = CATA181DEV.Device.DHCPv4.Server
DHCP4SERVERPOOL = DHCP4SERVER.Pool


class DHCPv4(CATA181DEV.Device.DHCPv4):
  ClientNumberOfEntries = tr.cwmptypes.ReadOnlyUnsigned(0)

  def __init__(self):
    super(DHCPv4, self).__init__()
    self.Server = Dhcp4Server()
    self.ClientList = {}
    self.Unexport(objects=['Relay'])


class Dhcp4Server(DHCP4SERVER):
  """tr-181 Device.DHCPv4.Server."""
  Enable = tr.cwmptypes.Bool(False)
  X_CATAWAMPUS_ORG_TextConfig = tr.cwmptypes.String('FakeCPE DHCP Config')

  def __init__(self):
    super(Dhcp4Server, self).__init__()
    self.PoolList = {}
    self.PoolList['1'] = Dhcp4ServerPool()

  @property
  def PoolNumberOfEntries(self):
    return len(self.PoolList)


class Dhcp4ServerPool(DHCP4SERVERPOOL):
  """tr-181 Device.DHCPv4.Server.Pool."""

  Enable = tr.cwmptypes.Bool(False)
  DNSServers = tr.cwmptypes.String('8.8.8.8')
  DomainName = tr.cwmptypes.String('example.com')
  Interface = tr.cwmptypes.String('')
  IPRouters = tr.cwmptypes.String('192.168.1.1')
  LeaseTime = tr.cwmptypes.Unsigned(86400)
  MinAddress = tr.cwmptypes.IP4Addr('192.168.1.32')
  MaxAddress = tr.cwmptypes.IP4Addr('192.168.1.63')
  Order = tr.cwmptypes.Int(1)
  SubnetMask = tr.cwmptypes.IP4Addr('192.168.1.255')
  X_CATAWAMPUS_ORG_NTPServers = tr.cwmptypes.String('')

  # Conditional serving parameters

  Chaddr = tr.cwmptypes.MacAddr('')
  ChaddrMask = tr.cwmptypes.MacAddr('')
  UserClassID = tr.cwmptypes.String('')
  VendorClassID = tr.cwmptypes.String('')
  VendorClassIDMode = tr.cwmptypes.Enum(['Substring'], init='Substring')

  class Option(DHCP4SERVERPOOL.Option):
    """tr-181 Device.DHCPv4.Server.Pool.Option."""
    Enable = tr.cwmptypes.Bool(True)
    Tag = tr.cwmptypes.Unsigned(0)
    Value = tr.cwmptypes.String('')

    def __init__(self):
      super(Dhcp4ServerPool.Option, self).__init__()
      self.Unexport(['Alias'])

  class StaticAddress(DHCP4SERVERPOOL.StaticAddress):
    """tr-181 Device.DHCPv4.Server.Pool.StaticAddress."""
    Enable = tr.cwmptypes.Bool(True)
    Chaddr = tr.cwmptypes.MacAddr(None)
    Yiaddr = tr.cwmptypes.IP4Addr(None)
    X_CATAWAMPUS_ORG_ClientID = tr.cwmptypes.String('')

    def __init__(self):
      super(Dhcp4ServerPool.StaticAddress, self).__init__()
      self.Unexport(['Alias'])

  def __init__(self):
    """Initialize the Dhcp4ServerPool."""
    super(Dhcp4ServerPool, self).__init__()
    self.ClientList = {}
    self.OptionList = {}
    self.StaticAddressList = {}
    self.Unexport(['Alias'])
    self.Unexport(['ReservedAddresses', 'ClientID', 'ChaddrExclude',
                   'ClientIDExclude', 'UserClassIDExclude',
                   'VendorClassIDExclude'])
    self._PopulateFakeClients()

  def _PopulateFakeClients(self):
    now = time.time()
    c = dhcp.Client(
        chaddr='00:11:22:33:44:11', ipaddr='192.168.133.7',
        expiry=now + 86400, clientid='client_id1')
    c.AddIP(ipaddr='192.168.1.1', expiry = now + 86400)
    self.ClientList['1'] = c
    self.ClientList['2'] = dhcp.Client(
        chaddr='00:11:22:33:44:33', ipaddr='192.168.133.8',
        expiry=now + (86400 * 2), clientid='client_id2',
        hostname='hostname_2', userclassid='userclassid_2',
        vendorclassid='vendorclassid_2')

  @property
  def Status(self):
    return 'Enabled' if self.Enable else 'Disabled'

  @property
  def StaticAddressNumberOfEntries(self):
    return len(self.StaticAddressList)

  @property
  def OptionNumberOfEntries(self):
    return len(self.OptionList)

  @property
  def ClientNumberOfEntries(self):
    return len(self.ClientList)

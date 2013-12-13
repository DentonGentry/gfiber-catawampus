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

import binascii
import datetime
import os
import string
import tr.core
import tr.helpers
import tr.mainloop
import tr.tr181_v2_6
import tr.types
import tr.x_catawampus_tr181_2_0

CATA181DEV = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
DHCP4SERVER = CATA181DEV.Device.DHCPv4.Server
DHCP4SERVERPOOL = DHCP4SERVER.Pool
DASH_TO_UNDERSCORE = string.maketrans('-', '_')

# unit tests can override these
DNSMASQCONFIG = ['/config/dnsmasq/acs.conf']
LOGCONFIG = True


# All DhcpServerPool objects write their config to one file.
# DhcpServers stores the set of DhcpServer objects which need
# to be saved when there is a configuration change.
DhcpServers = set()


# Dnsmasq uses tag: notations to indicate conditional serving
# pools. Tag names must be unique. We generate a tag randomly,
# and check whether it already exists.
DhcpPoolTags = set()


def _ReadFileActiveLines(filename):
  """Return all non-commented lines.

  For example:
    # This is a comment
    This would be dnsmasq configuration

  Would result in returning:
    ['This would be dnsmasq configuration']

  Args:
    filename: the file to read in.
  Returns:
    A list of active lines from filename.
  """
  try:
    activelines = []
    with open(filename) as f:
      for line in f:
        if not line:
          continue
        if not line.startswith('#'):
          activelines.append(line)
    return activelines
  except IOError:
    return []


def _LogConfig(prefix, lines):
  """Log each line with a prefixed reason code."""
  if not LOGCONFIG:
    return
  for line in lines:
    print 'dnsmasq.conf %s: %s' % (prefix, line)


@tr.mainloop.WaitUntilIdle
def WriteDnsmasqConfig():
  """Write out all configs and restart dnsmasq."""
  pools = []
  for s in DhcpServers:
    for (idx, pool) in s.PoolList.iteritems():
      pool.index = idx
      pools.append(pool)
  servers = sorted(pools, key=lambda server: server.Order)

  lines = []
  for server in servers:
    lines.extend(server.DnsmasqConfig())

  oldfilelines = _ReadFileActiveLines(DNSMASQCONFIG[0])
  if lines == oldfilelines:
    print 'dnsmasq config has not changed, not saving.\n'
    return

  _LogConfig('new', lines)
  try:
    with tr.helpers.AtomicFile(DNSMASQCONFIG[0]) as f:
      f.write('# saved by catawampus %s\n' % str(datetime.datetime.utcnow()))
      for line in lines:
        f.write(line)
  except IOError:
    print 'Unable to save dnsmasq config\n'
    return

  # TODO(dgentry): restart dnsmasq


class Dhcp4Server(DHCP4SERVER):
  """tr-181 Device.DHCPv4.Server."""
  Enable = tr.types.TriggerBool(False)
  X_CATAWAMPUS_ORG_TextConfig = tr.types.FileBacked(
      DNSMASQCONFIG, tr.types.String(), delete_if_empty=False)

  def __init__(self):
    super(Dhcp4Server, self).__init__()
    self.PoolList = {}
    DhcpServers.add(self)

  def Close(self):
    """Routine called by tr/core when an object is about to be deleted."""
    DhcpServers.remove(self)
    WriteDnsmasqConfig()

  @property
  def PoolNumberOfEntries(self):
    return len(self.PoolList)


class Dhcp4ServerPool(DHCP4SERVERPOOL):
  """tr-181 Device.DHCPv4.Server.Pool."""

  Enable = tr.types.TriggerBool(False)
  DNSServers = tr.types.TriggerString('')
  DomainName = tr.types.TriggerString('')
  Interface = tr.types.TriggerString('')
  IPRouters = tr.types.TriggerString('')
  LeaseTime = tr.types.TriggerUnsigned(86400)
  MinAddress = tr.types.TriggerIP4Addr(None)
  MaxAddress = tr.types.TriggerIP4Addr(None)
  Order = tr.types.TriggerInt(1)
  SubnetMask = tr.types.TriggerIP4Addr(None)
  X_CATAWAMPUS_ORG_NTPServers = tr.types.TriggerString('')

  # Conditional serving parameters

  Chaddr = tr.types.TriggerMacAddr('')
  # dnsmasq only allows octet masks
  ChaddrMask = tr.types.TriggerEnum(
      ['',
       '00:00:00:00:00:00', '00-00-00-00-00-00',
       'ff:00:00:00:00:00', 'FF:00:00:00:00:00',
       'ff:ff:00:00:00:00', 'FF:FF:00:00:00:00',
       'ff:ff:ff:00:00:00', 'FF:FF:FF:00:00:00',
       'ff:ff:ff:ff:00:00', 'FF:FF:FF:FF:00:00',
       'ff:ff:ff:ff:ff:00', 'FF:FF:FF:FF:FF:00',
       'ff:ff:ff:ff:ff:ff', 'FF:FF:FF:FF:FF:FF',
       'ff-00-00-00-00-00', 'FF-00-00-00-00-00',
       'ff-ff-00-00-00-00', 'FF-FF-00-00-00-00',
       'ff-ff-ff-00-00-00', 'FF-FF-FF-00-00-00',
       'ff-ff-ff-ff-00-00', 'FF-FF-FF-FF-00-00',
       'ff-ff-ff-ff-ff-00', 'FF-FF-FF-FF-FF-00',
       'ff-ff-ff-ff-ff-ff', 'FF-FF-FF-FF-FF-FF',
      ], init='')
  UserClassID = tr.types.TriggerString('')
  VendorClassID = tr.types.TriggerString('')
  # dnsmasq doesn't implement exact, prefix, or suffix matching.
  VendorClassIDMode = tr.types.TriggerEnum(['Substring'], init='Substring')

  class Option(DHCP4SERVERPOOL.Option):
    """tr-181 Device.DHCPv4.Server.Pool.Option."""
    Enable = tr.types.TriggerBool(True)
    Tag = tr.types.TriggerUnsigned(0)
    Value = tr.types.TriggerString('')

    def __init__(self):
      super(Dhcp4ServerPool.Option, self).__init__()
      self.Unexport(['Alias'])

    def Triggered(self):
      WriteDnsmasqConfig()

  class StaticAddress(DHCP4SERVERPOOL.StaticAddress):
    """tr-181 Device.DHCPv4.Server.Pool.StaticAddress."""
    Enable = tr.types.TriggerBool(True)
    Chaddr = tr.types.TriggerMacAddr(None)
    Yiaddr = tr.types.TriggerIP4Addr(None)
    X_CATAWAMPUS_ORG_ClientID = tr.types.TriggerString('')

    def __init__(self):
      super(Dhcp4ServerPool.StaticAddress, self).__init__()
      self.Unexport(['Alias'])

    def Triggered(self):
      WriteDnsmasqConfig()

  def _GetUnusedName(self):
    """Generate a unique tag for this object."""
    for i in range(10000):
      name = 't%d' % i
      if name not in DhcpPoolTags:
        return name

  def __init__(self, name=None):
    """Initialize the Dhcp4ServerPool.

    Args:
      name: the string to use in dnsmasq's tag: fields. If None, one will
        be generated automatically. A name can be passed in for unit tests.
    """
    super(Dhcp4ServerPool, self).__init__()
    self.name = name
    self.index = None
    self.StaticAddressList = {}
    self.OptionList = {}
    self.ClientList = {}
    self.Unexport(['Alias'])

    # We can't take individual addresses away from the pool.
    self.Unexport(['ReservedAddresses'])

    # dnsmasq cannot map a client-id to a pool of
    # addresses, and wanting to do so is kindof nonsensical
    # anyway. Using a Device.DHCPv4.Server.Pool.{i}.StaticAddress.{i}.
    # to map a specific client-id to a static IP address
    # makes more sense.
    self.Unexport(['ClientID'])

    # dnsmasq cannot do exclude matches
    self.Unexport(['ChaddrExclude', 'ClientIDExclude', 'UserClassIDExclude',
                   'VendorClassIDExclude'])

    if self.name is None:
      self.name = self._GetUnusedName()

    DhcpPoolTags.add(self.name)

  def Close(self):
    """Routine called by tr/core when an object is about to be deleted."""
    DhcpPoolTags.remove(self.name)
    WriteDnsmasqConfig()

  @property
  def Status(self):
    if not self.ValidateConfig(doprint=False):
      return 'Error_Misconfigured'
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

  def Triggered(self):
    WriteDnsmasqConfig()

  def ValidateConfig(self, doprint=True):
    a = self.MinAddress
    b = self.MaxAddress
    if (a and not b) or (not a and b):
      if doprint:
        print 'Invalid config %s, {Min,Max}Address must both be set' % self.name
      return False
    return True

  def _MacMaskToDnsmasq(self, mac, mask):
    """Combine a MAC address and mask to the dnsmasq wildcard format.

    Examples:
      '00:11:22:33:44:55' & 'ff:ff:ff:00:00:00' = '00:11:22:*:*:*'
      '00-11-22-33-44-55' & '00-00-00-00-00-00' = '*:*:*:*:*:*'
      '00:11:22:33:44:55' & 'ff:ff:ff:ff:ff:ff' = '00:11:22:33:44:55'
      '00:11:22:33:44:55' & ''                  = '00:11:22:33:44:55'

    Args:
      mac: a MAC address with octets separated by colons or dashes.
      mask: a MAC mask with octets separated by colons or dashes.

    Returns:
      a wildcarded address.
    """
    maskmap = {
        'ff:00:00:00:00:00': 1, 'ff:ff:00:00:00:00': 2,
        'ff:ff:ff:00:00:00': 3, 'ff:ff:ff:ff:00:00': 4,
        'ff:ff:ff:ff:ff:00': 5, 'ff:ff:ff:ff:ff:ff': 6,
        '00:00:00:00:00:00': 0, '': 6,
    }
    dash_to_colon = string.maketrans('-', ':')
    mac = str(mac).lower().translate(dash_to_colon)
    mask = str(mask).lower().translate(dash_to_colon)
    octets = mac.split(':')
    lim = maskmap.get(mask, 6)
    for i in range(lim, 6):
      octets[i] = '*'
    return ':'.join(octets)

  def DnsmasqConfig(self):
    """Return the list of lines to be written to the dnsmasq config."""
    minip = str(self.MinAddress)
    maxip = str(self.MaxAddress)
    lt = str(self.LeaseTime)
    name = str(self.name)
    lines = []

    restrict = ''
    if self.Chaddr or self.UserClassID or self.VendorClassID:
      restrict = 'tag:%s,' % name

    if minip and maxip and lt:
      l = 'dhcp-range=%s%s,%s,%s\n' % (restrict, minip, maxip, lt)
      lines.append(l)

    if self.UserClassID:
      l = 'dhcp-userclass=set:%s,%s\n' % (name, self.UserClassID)
      lines.append(l)
    if self.VendorClassID:
      l = 'dhcp-vendorclass=set:%s,%s\n' % (name, self.VendorClassID)
      lines.append(l)
    if self.Chaddr:
      match = self._MacMaskToDnsmasq(self.Chaddr, self.ChaddrMask)
      l = 'dhcp-host=%s,set:%s\n' % (match, name)
      lines.append(l)

    if self.DomainName:
      domain = str(self.DomainName)
      if restrict and minip and maxip:
        l = 'domain=%s,%s,%s\n' % (domain, minip, maxip)
      else:
        l = 'domain=%s\n' % domain
      lines.append(l)

    if self.IPRouters:
      l = 'dhcp-option=%soption:router,%s\n' % (restrict, self.IPRouters)
      lines.append(l)
    ntp = str(self.X_CATAWAMPUS_ORG_NTPServers)
    if ntp:
      l = 'dhcp-option=%soption:ntp-server,%s\n' % (restrict, ntp)
      lines.append(l)

    if self.DNSServers:
      l = 'dhcp-option=%soption:dns-server,%s\n' % (restrict, self.DNSServers)
      lines.append(l)

    for opt in self.OptionList.values():
      if not opt.Enable:
        continue
      val = binascii.unhexlify(str(opt.Value))
      l = ('dhcp-option=%soption:%d,%s\n' % (restrict, opt.Tag, val))
      lines.append(l)

    for s in self.StaticAddressList.values():
      if not s.Enable:
        continue
      if s.Chaddr:
        mac = str(s.Chaddr)
        l = 'dhcp-host=%s%s,%s\n' % (restrict, mac, s.Yiaddr)
        lines.append(l)
      if s.X_CATAWAMPUS_ORG_ClientID:
        cid = str(s.X_CATAWAMPUS_ORG_ClientID)
        l = 'dhcp-host=%sid:%s,%s\n' % (restrict, cid, s.Yiaddr)
        lines.append(l)

    return lines

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
import errno
import socket
import string
import struct
import subprocess
import traceback

import dhcp
import tr.basemodel
import tr.core
import tr.cwmptypes
import tr.helpers
import tr.mainloop
import tr.session

CATA181DEV = tr.basemodel
DHCP4SERVER = CATA181DEV.Device.DHCPv4.Server
DHCP4SERVERPOOL = DHCP4SERVER.Pool
DASH_TO_UNDERSCORE = string.maketrans('-', '_')

# unit tests can override these
DNSMASQCONFIG = ['/fiber/config/dnsmasq/cwmp.conf']
DNSMASQLEASES = ['/fiber/config/dhcp.leases']
LOGCONFIG = True
RESTARTCMD = ['restart', 'dnsmasq']


# All DhcpServerPool objects write their config to one file.
# DhcpServers stores the set of DhcpServer objects which need
# to be saved when there is a configuration change.
DhcpServers = set()


# Dnsmasq uses tag: notations to indicate conditional serving
# pools. Tag names must be unique. We generate a tag randomly,
# and check whether it already exists.
DhcpPoolTags = set()


# The URL of the ACS in use, which we'll export to our DHCP clients
# if nonempty.  (A one-element list, for ease of reassignment.)
DhcpAcsUrl = ['']


class _TriggerDict(dict):

  def __setitem__(self, k, v):
    dict.__setitem__(self, k, v)
    UpdateDnsmasqConfig()

  def __delitem__(self, k):
    dict.__delitem__(self, k)
    UpdateDnsmasqConfig()


def _ActiveLines(lines):
  """Return all non-commented lines.

  For example:
    # This is a comment
    This would be dnsmasq configuration

  Would result in returning:
    ['This would be dnsmasq configuration']

  Args:
    lines: the array of lines, as read from open().readlines().
  Returns:
    A list of active lines from filename.
  """
  activelines = []
  for line in lines:
    if not line.strip():
      continue
    if not line.startswith('#'):
      activelines.append(line)
  return activelines


def _ReadFileActiveLines(filename):
  """Return all _ActiveLines from the given filename."""
  try:
    f = open(filename)
  except IOError:
    return []
  else:
    return _ActiveLines(f)


def _LogConfig(prefix, lines):
  """Log each line with a prefixed reason code."""
  if not LOGCONFIG:
    return
  for line in lines:
    if line.endswith('\n'): line = line[:-1]
    print 'dnsmasq.conf %s: %s' % (prefix, line)


@tr.mainloop.WaitUntilIdle
def UpdateDnsmasqConfig():
  """Write out all configs and restart dnsmasq."""
  pools = []
  lines = []
  active = False
  for s in DhcpServers:
    for (idx, pool) in s.PoolList.iteritems():
      if pool.is_enabled is not None:
        active = True
      pool.index = idx
      pools.append(pool)

  if not active:
    print 'No DHCPv4 config received, skip writing dnsmasq.conf.'
    return

  # Include the value of the ACS server URL if possible.
  if DhcpAcsUrl and DhcpAcsUrl[0]:
    url = DhcpAcsUrl[0].replace('"', '').replace('\\', '')
    lines.extend([
        '# Set flag cwmp, when vendor-class contains dslforum.org\n',
        'dhcp-vendorclass=set:cwmp,enterprise:3561,dslforum.org\n',
        '# Sends ACS_URL if the client requested it\n',
        'dhcp-option=tag:cwmp,vi-encap:3561,option6:1,"%s"\n' % url,
        'dhcp-option=vi-encap:3561,11,"%s"\n' % url,
        '\n',
    ])

  servers = sorted(pools, key=lambda server: server.Order)
  for server in servers:
    lines.extend(server.DnsmasqConfig())

  oldfilelines = _ReadFileActiveLines(DNSMASQCONFIG[0])
  if _ActiveLines(lines) == oldfilelines:
    print 'dnsmasq config has not changed, not updating.'
    return

  _LogConfig('new', lines)
  try:
    with tr.helpers.AtomicFile(DNSMASQCONFIG[0]) as f:
      f.write('# saved by catawampus %s\n\n' % datetime.datetime.utcnow())
      for line in lines:
        f.write(line)
    subprocess.check_call(RESTARTCMD, close_fds=True)
  except (IOError, OSError, subprocess.CalledProcessError):
    print 'Unable to restart dnsmasq'
    traceback.print_exc()


def IpStringToNativeInt(ip4addr):
  """Convert w.x.y.z IP4 address to *native* byte order integer.

  IP addresses are conventionally in network byte order, which is
  big-endian. We instead want an integer in native byte order where
  we can do comparisons to see if an IP address is within a range.

  Arguments:
    ip4addr: a dotted quad string.
  Returns:
    an integer in *native* byte order, not network byte order.
  """
  try:
    return struct.unpack('!I', socket.inet_pton(socket.AF_INET, ip4addr))[0]
  except socket.error:
    return 0


class DHCPv4(CATA181DEV.Device.DHCPv4):
  """tr-181 Device.DHCPv4."""
  ClientNumberOfEntries = tr.cwmptypes.NumberOf('ClientList')

  def __init__(self, dmroot):
    super(DHCPv4, self).__init__()
    self.dmroot = dmroot
    self.Server = Dhcp4Server()
    self.ClientList = _TriggerDict()
    self.Unexport(objects=['Relay'])
    if self.dmroot:
      self._SetupUrlChanged()

  @tr.mainloop.WaitUntilIdle
  def _SetupUrlChanged(self):
    """We delay this setup so that Device.ManagementServer is populated."""
    tms = type(self.dmroot.Device.ManagementServer)
    if hasattr(tms, 'URL'):
      tms.URL.callbacklist.append(self._UrlChanged)
    else:
      print 'warning: dnsmasq: ManagementServer is missing URL element.'

  def _UrlChanged(self, unused_obj):
    url = self.dmroot.Device.ManagementServer.URL
    if not DhcpAcsUrl or DhcpAcsUrl[0] != url:
      print 'dnsmasq: ACS URL changed to %r' % url
      DhcpAcsUrl[0] = url
      UpdateDnsmasqConfig()


class Dhcp4ServerPool(DHCP4SERVERPOOL):
  """tr-181 Device.DHCPv4.Server.Pool."""

  DNSServers = tr.cwmptypes.TriggerIPv4AddrList('')
  DomainName = tr.cwmptypes.TriggerString('')
  Interface = tr.cwmptypes.TriggerString('')
  IPRouters = tr.cwmptypes.TriggerIPv4AddrList('')
  LeaseTime = tr.cwmptypes.TriggerUnsigned(86400)
  MinAddress = tr.cwmptypes.TriggerIP4Addr(None)
  MaxAddress = tr.cwmptypes.TriggerIP4Addr(None)
  Order = tr.cwmptypes.TriggerInt(1)
  SubnetMask = tr.cwmptypes.TriggerIP4Addr(None)
  X_CATAWAMPUS_ORG_NTPServers = tr.cwmptypes.TriggerString('')

  OptionNumberOfEntries = tr.cwmptypes.NumberOf('OptionList')
  StaticAddressNumberOfEntries = tr.cwmptypes.NumberOf('StaticAddressList')

  # Conditional serving parameters

  Chaddr = tr.cwmptypes.TriggerMacAddr('')
  # dnsmasq only allows octet masks
  ChaddrMask = tr.cwmptypes.TriggerEnum(
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
       'ff-ff-ff-ff-ff-ff', 'FF-FF-FF-FF-FF-FF'], init='')
  UserClassID = tr.cwmptypes.TriggerString('')
  VendorClassID = tr.cwmptypes.TriggerString('')
  # dnsmasq doesn't implement exact, prefix, or suffix matching.
  VendorClassIDMode = tr.cwmptypes.TriggerEnum(['Substring'], init='Substring')

  class Option(DHCP4SERVERPOOL.Option):
    """tr-181 Device.DHCPv4.Server.Pool.Option."""
    Enable = tr.cwmptypes.TriggerBool(True)
    Tag = tr.cwmptypes.TriggerUnsigned(0)
    Value = tr.cwmptypes.TriggerString('')

    def __init__(self):
      super(Dhcp4ServerPool.Option, self).__init__()
      self.Unexport(['Alias'])

    def Triggered(self):
      UpdateDnsmasqConfig()

  class StaticAddress(DHCP4SERVERPOOL.StaticAddress):
    """tr-181 Device.DHCPv4.Server.Pool.StaticAddress."""
    Enable = tr.cwmptypes.TriggerBool(True)
    Chaddr = tr.cwmptypes.TriggerMacAddr(None)
    Yiaddr = tr.cwmptypes.TriggerIP4Addr(None)
    X_CATAWAMPUS_ORG_ClientID = tr.cwmptypes.TriggerString('')

    def __init__(self):
      super(Dhcp4ServerPool.StaticAddress, self).__init__()
      self.Unexport(['Alias'])

    def Triggered(self):
      UpdateDnsmasqConfig()

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
    self.is_enabled = None
    self.StaticAddressList = _TriggerDict()
    self.OptionList = _TriggerDict()

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

  def __del__(self):
    DhcpPoolTags.remove(self.name)

  @property
  def Status(self):
    if not self.ValidateConfig():
      return 'Error_Misconfigured'
    return 'Enabled' if self.Enable else 'Disabled'

  @property
  def ClientNumberOfEntries(self):
    return len(self.ClientList)

  @property
  @tr.session.cache
  def ClientList(self):
    """Return a dict of known clients from dnsmasq leases file."""
    if not self.MinAddress or not self.MaxAddress:
      return {}
    min_ip_i = IpStringToNativeInt(self.MinAddress)
    max_ip_i = IpStringToNativeInt(self.MaxAddress)
    clients = {}
    try:
      line = ''
      idx = 1
      with open(DNSMASQLEASES[0]) as f:
        for line in f:
          try:
            (expiry, mac, ip, name, clientid) = line.strip().split()
          except ValueError:
            # dnsmasq.leases contains a few other types of lines, like the
            # DUID for IPv6: duid 00:01:00:01:02:03:04:05:06:07.
            # Just skip these.
            if 'duid' not in line:
              print 'Unable to process dnsmasq lease line: %s' % line
            continue
          ip_i = IpStringToNativeInt(ip)
          if not min_ip_i <= ip_i <= max_ip_i:
            # Must be from some other pool
            continue
          mac = mac.lower()
          clientid = '' if clientid == '*' else binascii.hexlify(clientid)
          name = '' if name == '*' else name
          c = dhcp.Client(chaddr=mac, ipaddr=ip, expiry=int(expiry),
                          clientid=clientid, hostname=name)
          clients[str(idx)] = c
          idx += 1
    except (OSError, IOError) as e:
      if e.errno != errno.ENOENT:
        print 'Unable to process dnsmasq lease file : %s' % DNSMASQLEASES[0]
    return clients

  def GetEnable(self):
    return self.is_enabled

  def SetEnable(self, value):
    self.is_enabled = bool(value)
    self.Triggered()

  Enable = property(GetEnable, SetEnable, None,
                    'Device.DHCPv4.Server.Pool.{x}.Enable')

  def Triggered(self):
    UpdateDnsmasqConfig()

  def ValidateConfig(self):
    if self.is_enabled is None:
      return False
    a = self.MinAddress
    b = self.MaxAddress
    if (a and not b) or (not a and b):
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

    lines = []
    if not self.Enable:
      return lines

    minip = str(self.MinAddress) if self.MinAddress else ''
    maxip = str(self.MaxAddress) if self.MaxAddress else ''
    lt = str(self.LeaseTime)
    name = str(self.name)

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

    static_ips = {}
    for s in self.StaticAddressList.values():
      if not s.Enable:
        continue
      ip = s.Yiaddr
      mappings = static_ips.get(ip, [])
      if s.Chaddr:
        mac = str(s.Chaddr)
        mappings.append(mac)
      if s.X_CATAWAMPUS_ORG_ClientID:
        cid = 'id:%s' % str(s.X_CATAWAMPUS_ORG_ClientID)
        mappings.append(cid)
      static_ips[ip] = mappings

    for (ip, mappings) in static_ips.iteritems():
      group = ','.join(mappings)
      l = 'dhcp-host=%s%s,%s\n' % (restrict, group, ip)
      lines.append(l)

    return lines


class Dhcp4Server(DHCP4SERVER):
  """tr-181 Device.DHCPv4.Server."""
  Pool = Dhcp4ServerPool
  PoolNumberOfEntries = tr.cwmptypes.NumberOf('PoolList')
  X_CATAWAMPUS_ORG_TextConfig = tr.cwmptypes.FileBacked(
      DNSMASQCONFIG, tr.cwmptypes.String(), delete_if_empty=False)

  def __init__(self):
    super(Dhcp4Server, self).__init__()
    self.is_enabled = None
    self.PoolList = _TriggerDict()
    DhcpServers.add(self)

  def Triggered(self):
    UpdateDnsmasqConfig()

  def GetEnable(self):
    return self.is_enabled

  def SetEnable(self, value):
    self.is_enabled = bool(value)
    self.Triggered()

  Enable = property(GetEnable, SetEnable, None, 'Device.DHCPv4.Server.Enable')

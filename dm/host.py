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

"""tr-181 Device.Hosts implementation.

Provides a way to discover network topologies.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import datetime
import os
import struct
import subprocess
import time
import tr.helpers
import tr.session
import tr.tr181_v2_6
import tr.types
import dhcp

BASE181HOSTS = tr.tr181_v2_6.Device_v2_6.Device.Hosts
BASE181HOST = tr.tr181_v2_6.Device_v2_6.Device.Hosts.Host
CATA181 = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
CATA181HOSTS = CATA181.Device.Hosts
CATA181HOST = CATA181HOSTS.Host

# Unit tests can override these
DHCP_FINGERPRINTS = '/config/dhcp.fingerprints'
IP6NEIGH = ['ip', '-6', 'neigh']
PROC_NET_ARP = '/proc/net/arp'
SYS_CLASS_NET_PATH = '/sys/class/net'
TIMENOW = time.time


def HexIntOrZero(arg):
  try:
    return int(arg, 0)
  except (ValueError, TypeError):
    return 0


class Hosts(BASE181HOSTS):
  """Implement tr-181 Device.Hosts table."""

  def __init__(self, iflookup=None, bridgename=None, dmroot=None):
    """Device.Hosts.

    Args:
      iflookup: a dict mapping Linux ifnames to tr-69
        parameter paths. Ex:
        {'eth0': 'Device.Ethernet.Interface.1.',
         'eth1': 'Device.MoCA.Interface.1.'}
      bridgename: name of the Linux bridge device. Ex: 'br0'
      dmroot: root of the Export tree (ex: there should be an
        InternetGatewayDevice attribute for tr-98)
    """
    super(Hosts, self).__init__()
    self.bridges = []
    self.iflookup = {}
    self.dmroot = dmroot
    if iflookup:
      self.iflookup = iflookup
    self.iflookup_built = False
    if bridgename:
      x = bridgename if type(bridgename) == list else [bridgename]
      self.bridges.extend(x)

  def _BuildIfLookup(self, iflookup):
    """Walk the device tree to create an interface mapping.

    Returns:
      a dict mapping Linux ifnames to tr-69 parameter paths. Ex:
       {'eth0': 'Device.Ethernet.Interface.1',
        'eth1': 'Device.MoCA.Interface.1'}
    """
    for (l1interface, wifi) in self._GetTr98WifiObjects():
      iflookup[wifi.Name] = l1interface
    for (l1interface, moca) in self._GetTr181MocaObjects():
      iflookup[moca.Name] = l1interface
    for (l1interface, enet) in self._GetTr181EthernetObjects():
      iflookup[enet.Name] = l1interface
    return iflookup

  def Iflookup(self):
    """Returns iflookup table."""
    if not self.iflookup_built:
      self._BuildIfLookup(self.iflookup)
      self.iflookup_built = True
    return self.iflookup

  def _AddIpToHostDict(self, entry, ip):
    """Add ip to entry['ip4'] or entry['ip6'], as appropriate.

    First, determine whether address should go in the 'ip4'
    key or the 'ip6' key.

    If entry already contains the key, append the ip
    argument to it. Otherwise, create an entry

    Args:
      entry: the dict for a host entry
      ip: the IP address to add, like '1.2.3.4'

    Returns:
      the entry
    """
    key = 'ip6' if tr.helpers.IsIP6Addr(ip) else 'ip4'
    iplist = entry.get(key, [])
    if ip not in iplist:
      iplist.append(ip)
    entry[key] = iplist
    return entry

  def _AddLayer1Interface(self, entry, iface):
    """Populate Layer1Interface in entry.

    If entry['Layer1Interface'] does not exist, always populate it
    (even with an empty string).
    Otherwise, replace entry['Layer1Interface'] if we have better
    information.
    """
    l1 = self.Iflookup().get(iface, '')
    if l1:
      entry['Layer1Interface'] = l1
    elif 'Layer1Interface' not in entry:
      entry['Layer1Interface'] = ''

  def _GetInterfacesInBridge(self, brname):
    """Return list of all interfaces in brname."""
    if_path = os.path.join(SYS_CLASS_NET_PATH, brname, 'brif')
    return sorted(os.listdir(if_path))

  def _GetHostsInBridge(self, brname):
    """Iterate over all client addresses in the FDB of brname.

    Args:
      brname: name of the bridge netdev, like 'br0'

    Yields:
      iterable of (mac, iface) where:
        mac: MAC address of the station
        iface: name of the interface where the MAC was seen, like 'eth0'
    """
    interfaces = dict()
    for (idx, ifc) in enumerate(self._GetInterfacesInBridge(brname), start=1):
      interfaces[idx] = ifc
    fdb_path = os.path.join(SYS_CLASS_NET_PATH, brname, 'brforward')
    with open(fdb_path) as f:
      fdb = f.read()  # proc file only works if read all at once
      offset = 0
      while offset < len(fdb):
        (m1, m2, m3, m4, m5, m6, port_lo, unused_local, unused_age_timer,
         port_hi, unused_pad1, unused_pad2) = struct.unpack(
             'BBBBBBBBIBBH', fdb[offset:offset+16])
        mac = '%02x:%02x:%02x:%02x:%02x:%02x' % (m1, m2, m3, m4, m5, m6)
        port = (port_hi << 8) | port_lo
        iface = interfaces.get(port, 'unknown')
        yield (mac, iface)
        offset += 16

  def _GetHostsFromBridges(self, hosts):
    """Populate dict of known hosts on bridge devices.

    Walks through the bridge forwarding table.

    Args:
      hosts: a dict (with MAC addresses as keys) of fields
        to be populated for Device.Hosts.Host
    """
    for brname in self.bridges:
      try:
        for (mac, iface) in self._GetHostsInBridge(brname):
          host = hosts.get(mac, dict())
          self._AddLayer1Interface(host, iface)
          host['PhysAddress'] = mac
          host['Active'] = True
          hosts[mac] = host
      except (OSError, IOError):
        print '_GetHostsFromBridges unable to process %s' % brname

  def _ParseArpTable(self):
    """Parse /proc/net/arp and return it as a list.

    Returns:
      a list of (mac, ip, dev) tuples, like:
        [('f8:8f:ca:00:00:01', '1.1.1.1', 'eth0'),
         ('f8:8f:ca:00:00:02', '1.1.1.2', 'eth1')]
    """
    ATF_COM = 0x02
    with open(PROC_NET_ARP) as f:
      unused_headers = f.readline()
      result = []
      for line in f:
        fields = line.split()
        ip4 = fields[0]
        flg = HexIntOrZero(fields[2])
        mac = fields[3]
        dev = fields[5]
        if flg & ATF_COM:
          # Only report entries which are complete, not 00:00:00:00:00:00
          result.append((mac, ip4, dev))
    return result

  def _GetHostsFromArpTable(self, hosts):
    """Populate a dict of known hosts from /proc/net/arp.

    Args:
      hosts: a dict (with MAC addresses as keys) of fields
        to be populated for Device.Hosts.Host
    """
    for (mac, ip4, iface) in self._ParseArpTable():
      host = hosts.get(mac, dict())
      self._AddLayer1Interface(host, iface)
      host['PhysAddress'] = mac
      host['Active'] = True
      self._AddIpToHostDict(entry=host, ip=ip4)
      hosts[mac] = host

  def _ParseIp6Neighbors(self):
    """Parse "ip -6 neigh" and return it as a list.

    Returns:
      a list of (mac, ip, dev, active) tuples, like:
        [('f8:8f:ca:00:00:01', '1001::0001', 'eth0', True),
         ('f8:8f:ca:00:00:02', '1001::0001', 'eth1', False)]
    """
    ip6neigh = subprocess.Popen(IP6NEIGH, stdout=subprocess.PIPE)
    out, _ = ip6neigh.communicate(None)
    result = []

    for line in out.splitlines():
      fields = line.split()
      if len(fields) < 5:
        continue
      ip6 = fields[0]
      dev = fields[2]
      mac = fields[4]
      active = 'REACHABLE' in line
      result.append((mac, ip6, dev, active))
    return result

  def _GetHostsFromIp6Neigh(self, hosts):
    """Populate a dict of known hosts from IP6 neighbors.

    Args:
      hosts: a dict (with MAC addresses as keys) of fields
        to be populated for Device.Hosts.Host
    """
    for (mac, ip6, iface, active) in self._ParseIp6Neighbors():
      host = hosts.get(mac, dict())
      self._AddLayer1Interface(host, iface)
      host['PhysAddress'] = mac
      if active:
        # Only store if known active. We don't want to override
        # Active=True from some other source.
        host['Active'] = active
      self._AddIpToHostDict(entry=host, ip=ip6)
      hosts[mac] = host

  def _GetTr98WifiObjects(self):
    """Yield tr-98 WLANConfiguration objects, if any."""
    try:
      lan = self.dmroot.GetExport('InternetGatewayDevice.LANDevice.1')
    except (AttributeError, KeyError):
      return
    for (idx, wifi) in lan.WLANConfigurationList.iteritems():
      l1if = 'InternetGatewayDevice.LANDevice.1.WLANConfiguration.%s' % idx
      yield (l1if, wifi)

  def _GetHostsFromWifiAssociatedDevices(self, hosts):
    """Populate a dict of known hosts from wifi clients.

    Args:
      hosts: a dict (with MAC addresses as keys) of fields
        to be populated for Device.Hosts.Host
    """
    for (l1interface, wifi) in self._GetTr98WifiObjects():
      for (idx, device) in wifi.AssociatedDeviceList.iteritems():
        assocdev = l1interface + '.AssociatedDevice.' + str(idx)
        mac = device.AssociatedDeviceMACAddress.lower()
        host = hosts.get(mac, dict())
        host['AssociatedDevice'] = assocdev
        host['Layer1Interface'] = l1interface
        host['PhysAddress'] = mac
        host['Active'] = True
        hosts[mac] = host

  def _GetTr181MocaObjects(self):
    """Yield tr-181 Device.MoCA. objects, if any."""
    try:
      moca = self.dmroot.GetExport('Device.MoCA')
    except (AttributeError, KeyError):
      return
    for (idx, interface) in moca.InterfaceList.iteritems():
      l1if = 'Device.MoCA.Interface.%s' % idx
      yield (l1if, interface)

  def _GetHostsFromMocaAssociatedDevices(self, hosts):
    """Populate a dict of known hosts from MoCA clients.

    Args:
      hosts: a dict (with MAC addresses as keys) of fields
        to be populated for Device.Hosts.Host
    """
    for (l1interface, moca) in self._GetTr181MocaObjects():
      for (idx, device) in moca.AssociatedDeviceList.iteritems():
        assocdev = l1interface + '.AssociatedDevice.' + str(idx)
        mac = device.MACAddress.lower()
        host = hosts.get(mac, dict())
        host['AssociatedDevice'] = assocdev
        host['Layer1Interface'] = l1interface
        host['PhysAddress'] = mac
        host['Active'] = True
        hosts[mac] = host

  def _GetTr181Dhcp4ServerPools(self):
    """Yield tr-181 Device.DHCPv4.Server.Pool objects, if any."""
    try:
      dhcp4 = self.dmroot.GetExport('Device.DHCPv4.Server')
    except (AttributeError, KeyError):
      return
    for (idx, pool) in dhcp4.PoolList.iteritems():
      server = 'Device.DHCPv4.Server.Pool.%s.' % idx
      yield (server, pool)

  def _PopulateDhcpLeaseTime(self, host, client):
    """Populate LeaseTimeRemaining.

    Args:
      host: a dict to be passed to Host()
      client: a Device.DHCPv4.Server.Pool.Client
    """
    if client.IPv4AddressList:
      # Device.Hosts cannot express unique lease times per IP; pick the first.
      remain = client.IPv4AddressList.values()[0].LeaseTimeRemaining
      if remain:
        now = datetime.datetime.now()
        delta = (remain - now).total_seconds()
        host['LeaseTimeRemaining'] = delta if delta > 0 else 0

  def _PopulateFromDhcpOptions(self, host, client):
    """Populate Device.Hosts.Host from DHCP client options.

    Args:
      host: a dict to be passed to Host()
      client: a Device.DHCPv4.Server.Pool.Client
    """
    for option in client.OptionList.values():
      # DHCP Options tags
      if option.Tag == dhcp.HN:
        host['HostName'] = option.Value
      elif option.Tag == dhcp.CL:
        host['ClientID'] = option.Value
      elif option.Tag == dhcp.UC:
        host['UserClassID'] = option.Value
      elif option.Tag == dhcp.VC:
        host['VendorClassID'] = option.Value

  def _GetHostsFromDhcpServers(self, hosts):
    """Populate a dict of known hosts from DHCPv4 servers.

    Args:
      hosts: a dict (with MAC addresses as keys) of fields
        to be populated for Device.Hosts.Host
    """
    for (server, pool) in self._GetTr181Dhcp4ServerPools():
      for (idx, client) in pool.ClientList.iteritems():
        mac = client.Chaddr.lower()
        host = hosts.get(mac, dict())
        host['PhysAddress'] = mac
        host['DHCPClient'] = server + 'Client.' + str(idx)
        for v in client.IPv4AddressList.values():
          self._AddIpToHostDict(host, v.IPAddress)
        self._PopulateDhcpLeaseTime(host, client)
        self._PopulateFromDhcpOptions(host, client)
        hosts[mac] = host

  def _GetTr181EthernetObjects(self):
    """Yield tr-181 Device.Ethernet.Interface objects, if any."""
    try:
      eth = self.dmroot.GetExport('Device.Ethernet')
    except (AttributeError, KeyError):
      return
    for (idx, iface) in eth.InterfaceList.iteritems():
      l1interface = 'Device.Ethernet.Interface.%s' % idx
      yield (l1interface, iface)

  def _GetHostsFromEthernets(self, hosts):
    """Populate a dict of known hosts from Ethernet interfaces.

    Args:
      hosts: a dict (with MAC addresses as keys) of fields
        to be populated for Device.Hosts.Host
    """
    for (l1interface, iface) in self._GetTr181EthernetObjects():
      if not hasattr(iface, 'GetAssociatedDevices'):
        continue
      for client in iface.GetAssociatedDevices():
        mac = client['PhysAddress']
        host = hosts.get(mac, dict())
        host['PhysAddress'] = mac
        host['Layer1Interface'] = l1interface
        host['Active'] = True
        hosts[mac] = host

  @tr.session.cache
  def _GetHostList(self):
    """Return the list of known Hosts on all interfaces."""
    hosts = dict()
    self._GetHostsFromArpTable(hosts=hosts)
    self._GetHostsFromIp6Neigh(hosts=hosts)
    self._GetHostsFromBridges(hosts=hosts)
    self._GetHostsFromEthernets(hosts=hosts)
    self._GetHostsFromWifiAssociatedDevices(hosts=hosts)
    self._GetHostsFromMocaAssociatedDevices(hosts=hosts)
    self._GetHostsFromDhcpServers(hosts=hosts)
    host_list = dict()
    for idx, host in enumerate(hosts.values(), start=1):
      host_list[str(idx)] = Host(**host)
    return host_list

  @property
  def HostList(self):
    return self._GetHostList()

  @property
  def HostNumberOfEntries(self):
    return len(self.HostList)


class Host(CATA181HOST):
  """A single network entity; a host system on the network.

  This is an ephemeral object, created from some data source and
  peristing only for the duration of one CWMP session.
  """
  Active = tr.types.ReadOnlyBool(False)
  AddressSource = tr.types.ReadOnlyString('None')
  AssociatedDevice = tr.types.ReadOnlyString('')
  ClientID = tr.types.ReadOnlyString('')
  DHCPClient = tr.types.ReadOnlyString('')
  HostName = tr.types.ReadOnlyString('')
  Layer1Interface = tr.types.ReadOnlyString('')
  Layer3Interface = tr.types.ReadOnlyString('')
  LeaseTimeRemaining = tr.types.ReadOnlyInt(0)
  PhysAddress = tr.types.ReadOnlyString('')
  UserClassID = tr.types.ReadOnlyString('')
  VendorClassID = tr.types.ReadOnlyString('')

  def __init__(self, Active=False, PhysAddress='', ip4=None, ip6=None,
               DHCPClient='', AddressSource='None', AssociatedDevice='',
               Layer1Interface='', Layer3Interface='', HostName='',
               LeaseTimeRemaining=0, VendorClassID='',
               ClientID='', UserClassID=''):
    super(Host, self).__init__()
    self.Unexport(['Alias'])

    type(self).Active.Set(self, Active)
    type(self).AssociatedDevice.Set(self, AssociatedDevice)
    type(self).AddressSource.Set(self, AddressSource)
    type(self).ClientID.Set(self, ClientID)
    type(self).DHCPClient.Set(self, DHCPClient)
    type(self).HostName.Set(self, HostName)
    self.IPv4AddressList = self._PopulateIpList(ip4, HostIPv4Address)
    self.IPv6AddressList = self._PopulateIpList(ip6, HostIPv6Address)
    type(self).Layer1Interface.Set(self, Layer1Interface)
    type(self).Layer3Interface.Set(self, Layer3Interface)
    type(self).LeaseTimeRemaining.Set(self, int(LeaseTimeRemaining))
    type(self).PhysAddress.Set(self, PhysAddress)
    type(self).UserClassID.Set(self, UserClassID)
    type(self).VendorClassID.Set(self, VendorClassID)

  def _PopulateIpList(self, l, obj):
    """Return a dict with d[n] for each item in l."""
    d = dict()
    if l is None:
      return d
    for n, address in enumerate(l, start=1):
      d[str(n)] = obj(address=address)
    return d

  @property
  def IPv4AddressNumberOfEntries(self):
    return len(self.IPv4AddressList)

  @property
  def IPv6AddressNumberOfEntries(self):
    return len(self.IPv6AddressList)

  @property
  def IPAddress(self):
    return self.IP4Address or self.IP6Address

  @property
  def IP4Address(self):
    ip4 = self.IPv4AddressList.get('1', '')
    if ip4:
      return ip4.IPAddress
    return ''

  @property
  def IP6Address(self):
    ip6 = self.IPv6AddressList.get('1', '')
    if ip6:
      return ip6.IPAddress
    return ''

  @property
  def X_CATAWAMPUS_ORG_ClientIdentification(self):
    return ClientIdentification(self.PhysAddress)


class HostIPv4Address(BASE181HOST.IPv4Address):
  IPAddress = tr.types.ReadOnlyString('')

  def __init__(self, address=''):
    super(HostIPv4Address, self).__init__()
    type(self).IPAddress.Set(self, address)


class HostIPv6Address(BASE181HOST.IPv6Address):
  IPAddress = tr.types.ReadOnlyString('')

  def __init__(self, address=''):
    super(HostIPv6Address, self).__init__()
    type(self).IPAddress.Set(self, address)


class ClientIdentification(CATA181HOST.X_CATAWAMPUS_ORG_ClientIdentification):
  DhcpFingerprint = tr.types.ReadOnlyString('')

  def __init__(self, macaddr):
    super(ClientIdentification, self).__init__()
    fp = self._GetDhcpFingerprint(macaddr)
    type(self).DhcpFingerprint.Set(self, fp)

  def _GetDhcpFingerprint(self, macaddr):
    try:
      with open(DHCP_FINGERPRINTS) as f:
        for line in f:
          fields = line.split()
          if len(fields) != 2:
            continue
          (mac, fingerprint) = fields
          if mac.strip() == macaddr:
            return fingerprint.strip()
    except IOError:
      pass
    return ''

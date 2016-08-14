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

# unittest requires method names starting in 'test'
# pylint:disable=invalid-name
# pylint:disable=unused-argument

"""Integration test for host.py implementation.

Device.Hosts can get information from a number of sources:
  + Device.DHCPv4.Server.Pool (dm/dnsmasq.py)
  + Device.MoCA.Interface.AssociatedDevice (dm/brcmmoca2.py)
  + Device.Ethernet.Interface.GetAssociatedDevice
    (dm/ethernet.py and dm/qca83xx_ethernet.py)
  + InternetGatewayDevice.LANDevice.1.WLANConfiguration (dm/brcmwifi.py)

This test uses the real device model implementations, hooked up to
fake data sources, to test Device.Hosts.

To maintain sanity, the following test hosts are used:

00:01:02:11:00:01 192.168.1.1 : MoCA client, IP address from DHCP
                  fe80::0001:02ff:fe11:0001
00:01:02:22:00:01 192.168.1.2 : Ethernet client, IP address from ARP
                  fe80::0001:02ff:fe22:0001
00:01:02:33:00:01 192.168.1.3 : QCA8337 Ethernet client, IP address from ARP
                  no IPv6 address
00:01:02:44:00:01 -           : Wifi client, IP address not known
                  no IPv6 address

MoCA: moca0, Device.MoCA.Interface.1
Ethernet: eth0, Device.Ethernet.Interface.1
Wifi: wifi0, InternetGatewayDevice.LANDevice.1.WLANConfiguration.1
QCA8337: lan0, Device.Ethernet.Interface.2
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
from tr.wvtest import unittest
import tr.core
import tr.handle
import brcmmoca2
import brcmwifi
import dnsmasq
import ethernet
import host
import qca83xx_ethernet


class TestDeviceModelRoot(tr.core.Exporter):

  def __init__(self):
    super(TestDeviceModelRoot, self).__init__()
    self.Device = Device(dmroot=tr.handle.Handle(self))
    self.InternetGatewayDevice = InternetGatewayDevice()
    self.Export(['Device', 'InternetGatewayDevice'])


class Device(tr.core.Exporter):

  def __init__(self, dmroot):
    super(Device, self).__init__()
    self.DHCPv4 = dnsmasq.DHCPv4(dmroot=dmroot)
    self.Ethernet = Ethernet()
    self.Hosts = host.Hosts(dmroot=dmroot, bridgename='br0')
    self.MoCA = MoCA()
    self.Export(['DHCPv4', 'Ethernet', 'Hosts', 'MoCA'])
    pool = self.DHCPv4.Server.Pool()
    pool.MinAddress = '192.168.1.1'
    pool.MaxAddress = '192.168.1.255'
    self.DHCPv4.Server.PoolList['1'] = pool


class Ethernet(tr.core.Exporter):
  """Device.Ethernet."""

  def __init__(self):
    super(Ethernet, self).__init__()
    self.InterfaceList = {
        '1': ethernet.EthernetInterfaceLinux26(ifname='eth0'),
        '2': qca83xx_ethernet.EthernetInterfaceQca83xx(
            portnum=1, mac='00:00:00:00:00:00', ifname='lan0')
    }


class MoCA(tr.core.Exporter):
  """Device.MoCA."""

  def __init__(self):
    super(MoCA, self).__init__()
    self.InterfaceList = {'1': brcmmoca2.BrcmMocaInterface(ifname='moca0')}


class MockQca83xxPort(object):
  """A virtual QCA83xx switch port."""

  def __init__(self, port):
    self.port = port

  def CableDiag(self):
    return [('normal', 1), ('normal', 1), ('normal', 1), ('normal', 1)]

  def Duplex(self, duplex=None):
    return 'half'

  def Fdb(self):
    return [{'PhysAddress': '00:01:02:33:00:01', 'Ports': ['qca83xx_1']}]

  def IsLinkUp(self):
    return False

  def Speed(self, speed=None):
    return 10

  def Stats(self):
    return {}


class InternetGatewayDevice(tr.core.Exporter):

  def __init__(self):
    super(InternetGatewayDevice, self).__init__()
    self.LANDeviceList = {'1': LANDevice()}
    self.Export(lists=['LANDevice'])


class LANDevice(tr.core.Exporter):
  """InternetGatewayDevice.LANDevice."""

  def __init__(self):
    super(LANDevice, self).__init__()
    wifi = brcmwifi.BrcmWifiWlanConfiguration(ifname='wifi0')
    self.WLANConfigurationList = {'1': wifi}


class HostIntegrationTest(unittest.TestCase):

  def setUp(self):
    self.old_IP6NEIGH = host.IP6NEIGH[0]
    self.old_PROC_NET_ARP = host.PROC_NET_ARP
    self.old_SYS_CLASS_NET_PATH = host.SYS_CLASS_NET_PATH
    host.IP6NEIGH[0] = 'testdata/host_integration/ip6neigh'
    host.PROC_NET_ARP = 'testdata/host_integration/proc_net_arp'
    host.SYS_CLASS_NET_PATH = 'testdata/host_integration/sys/class/net'
    self.old_DNSMASQLEASES = dnsmasq.DNSMASQLEASES[0]
    dnsmasq.DNSMASQLEASES[0] = 'testdata/host_integration/dnsmasq.leases'
    self.old_MOCAP = brcmmoca2.MOCAP
    brcmmoca2.MOCAP = 'testdata/host_integration/mocap'
    self.old_QCAPORT = qca83xx_ethernet.QCAPORT
    qca83xx_ethernet.QCAPORT = MockQca83xxPort
    self.old_WL_EXE = brcmwifi.WL_EXE
    brcmwifi.WL_EXE = 'testdata/host_integration/wl'
    self.dmroot = TestDeviceModelRoot()
    self.dmh = tr.handle.Handle(self.dmroot)

  def tearDown(self):
    host.IP6NEIGH[0] = self.old_IP6NEIGH
    host.PROC_NET_ARP = self.old_PROC_NET_ARP
    host.SYS_CLASS_NET_PATH = self.old_SYS_CLASS_NET_PATH
    dnsmasq.DNSMASQLEASES[0] = self.old_DNSMASQLEASES
    brcmmoca2.MOCAP = self.old_MOCAP
    qca83xx_ethernet.QCAPORT = self.old_QCAPORT
    brcmwifi.WL_EXE = self.old_WL_EXE

  def testHosts(self):
    hl = self.dmroot.Device.Hosts.HostList
    print [h.PhysAddress for h in hl.values()]
    self.assertEqual(len(hl), 4)
    found = 0
    for h in hl.values():
      self.assertTrue(h.Active)
      if h.PhysAddress == '00:01:02:11:00:01':
        self.assertEqual(h.IPAddress, '192.168.1.1')
        self.assertEqual(h.IP4Address, '192.168.1.1')
        self.assertEqual(h.IP6Address, 'fe80::1:2ff:fe11:1')
        self.assertEqual(h.Layer1Interface, 'Device.MoCA.Interface.1')
        found |= 1
      elif h.PhysAddress == '00:01:02:22:00:01':
        self.assertEqual(h.IPAddress, '192.168.1.2')
        self.assertEqual(h.IP4Address, '192.168.1.2')
        self.assertEqual(h.IP6Address, 'fe80::1:2ff:fe22:1')
        self.assertEqual(h.Layer1Interface, 'Device.Ethernet.Interface.1')
        found |= 2
      elif h.PhysAddress == '00:01:02:33:00:01':
        self.assertEqual(h.IPAddress, '192.168.1.3')
        self.assertEqual(h.IP4Address, '192.168.1.3')
        self.assertEqual(h.IP6Address, '')
        self.assertEqual(h.Layer1Interface, 'Device.Ethernet.Interface.2')
        found |= 4
      elif h.PhysAddress == '00:01:02:44:00:01':
        self.assertEqual(h.IPAddress, '')
        self.assertEqual(h.IP4Address, '')
        self.assertEqual(h.IP6Address, '')
        wifi = 'InternetGatewayDevice.LANDevice.1.WLANConfiguration.1'
        self.assertEqual(h.Layer1Interface, wifi)
        found |= 8
      else:
        # Unexpected MAC address
        self.assertFalse(True)
    self.assertEqual(found, 0xF)


if __name__ == '__main__':
  unittest.main()

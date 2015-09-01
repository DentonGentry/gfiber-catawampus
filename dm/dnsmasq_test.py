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

"""Unit tests for dnsmasq implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os.path
import shutil
import tempfile
import google3
import dnsmasq
import management_server
import tr.cpe_management_server
import tr.handle
import tr.mainloop
import tr.session
from tr.wvtest import unittest


class DnsmasqTest(unittest.TestCase):
  """Tests for dnsmasq.py."""

  def setUp(self):
    super(DnsmasqTest, self).setUp()
    self.loop = tr.mainloop.MainLoop()
    tr.session.cache.flush()
    self.config_dir = tempfile.mkdtemp()
    dnsmasq.DhcpServers.clear()
    self.old_DNSMASQCONFIG = dnsmasq.DNSMASQCONFIG
    dnsmasq.DNSMASQCONFIG[0] = os.path.join(self.config_dir, 'config')
    self.old_DNSMASQLEASES = dnsmasq.DNSMASQLEASES
    dnsmasq.DNSMASQLEASES[0] = 'testdata/dnsmasq/leases'
    dnsmasq.LOGCONFIG = False
    dnsmasq.DhcpAcsUrl[0] = ''
    self.old_RESTARTCMD = dnsmasq.RESTARTCMD
    self.restartfile = os.path.join(self.config_dir, 'restarted')
    dnsmasq.RESTARTCMD = ['testdata/dnsmasq/restart', self.restartfile]
    self.dh4 = dnsmasq.Dhcp4Server()
    self.dh4p = dnsmasq.Dhcp4ServerPool(name='test')
    self.dh4.PoolList[1] = self.dh4p

  def tearDown(self):
    self.dh4p.Close()
    self.dh4.Close()
    self.dh4p = None
    self.dh4 = None
    dnsmasq.DNSMASQCONFIG = self.old_DNSMASQCONFIG
    dnsmasq.DNSMASQLEASES = self.old_DNSMASQLEASES
    shutil.rmtree(self.config_dir)
    super(DnsmasqTest, self).tearDown()

  def testValidateExports(self):
    dh4 = dnsmasq.DHCPv4(dmroot=None)
    tr.handle.ValidateExports(dh4)
    dh4p = dnsmasq.Dhcp4ServerPool()
    tr.handle.ValidateExports(dh4p)

  def testAcsUrl(self):
    class FakeAcsConfig(object):

      def __init__(self):
        self.url = None

      def SetAcsUrl(self, value):
        print 'SetAcsUrl(%r)' % value
        self.url = value
        return self.url

      def GetAcsUrl(self):
        return self.url

    dmroot = tr.core.Exporter()
    unused_dh4 = dnsmasq.DHCPv4(dmroot=dmroot)

    dmroot.Device = tr.core.Exporter()
    _mgmt = tr.cpe_management_server.CpeManagementServer(
        acs_config=FakeAcsConfig(),
        port=12345,
        ping_path='http://localhost')
    mgmt = management_server.ManagementServer181(_mgmt)
    dmroot.Device.ManagementServer = mgmt

    self.loop.RunOnce()
    self.assertEqual(dnsmasq._ReadFileActiveLines(dnsmasq.DNSMASQCONFIG[0]),
                     [])

    mgmt.URL = 'http://localhost'
    # no idle cycle yet, so config not rewritten
    self.assertEqual(dnsmasq._ReadFileActiveLines(dnsmasq.DNSMASQCONFIG[0]),
                     [])
    self.loop.RunOnce()
    # now it should be updated.
    cfg = dnsmasq._ReadFileActiveLines(dnsmasq.DNSMASQCONFIG[0])
    self.assertNotEqual(cfg, [])
    cfg = '|'.join(cfg)
    self.assertTrue('option6:1,"http://localhost"' in cfg)
    self.assertTrue('11,"http://localhost"' in cfg)

    mgmt.URL = 'http://localh"ost\\2'
    self.loop.RunOnce()
    cfg = dnsmasq._ReadFileActiveLines(dnsmasq.DNSMASQCONFIG[0])
    self.assertNotEqual(cfg, [])
    cfg = '|'.join(cfg)
    self.assertTrue('option6:1,"http://localhost2"' in cfg)
    self.assertTrue('11,"http://localhost2"' in cfg)

  def testAtomicWrite(self):
    dh4p = self.dh4p
    dh4p.Enable = True
    dh4p.MinAddress = '1.1.1.1'
    dh4p.MaxAddress = '2.2.2.2'
    self.assertFalse(os.path.exists(dnsmasq.DNSMASQCONFIG[0]))
    dh4p.DomainName = 'example.com'
    self.assertFalse(os.path.exists(dnsmasq.DNSMASQCONFIG[0]))
    self.loop.RunOnce(timeout=1)
    self.assertTrue(os.path.exists(dnsmasq.DNSMASQCONFIG[0]))

  def testChaddrMaskToDnsmasq(self):
    f = self.dh4p._MacMaskToDnsmasq
    mac = '00:11:22:33:44:55'
    self.assertEqual(f(mac=mac, mask='ff:ff:ff:ff:ff:ff'), '00:11:22:33:44:55')
    self.assertEqual(f(mac=mac, mask='ff:ff:ff:ff:ff:00'), '00:11:22:33:44:*')
    self.assertEqual(f(mac=mac, mask='ff:ff:ff:ff:00:00'), '00:11:22:33:*:*')
    self.assertEqual(f(mac=mac, mask='ff:ff:ff:00:00:00'), '00:11:22:*:*:*')
    self.assertEqual(f(mac=mac, mask='ff:ff:00:00:00:00'), '00:11:*:*:*:*')
    self.assertEqual(f(mac=mac, mask='ff:00:00:00:00:00'), '00:*:*:*:*:*')
    self.assertEqual(f(mac=mac, mask='00:00:00:00:00:00'), '*:*:*:*:*:*')
    self.assertEqual(f(mac=mac, mask=''), '00:11:22:33:44:55')
    mac = '00-11-22-33-44-55'
    self.assertEqual(f(mac=mac, mask='ff-ff-ff-ff-ff-ff'), '00:11:22:33:44:55')
    self.assertEqual(f(mac=mac, mask='ff-ff-ff-ff-ff-00'), '00:11:22:33:44:*')
    self.assertEqual(f(mac=mac, mask='ff-ff-ff-ff-00-00'), '00:11:22:33:*:*')
    self.assertEqual(f(mac=mac, mask='ff-ff-ff-00-00-00'), '00:11:22:*:*:*')
    self.assertEqual(f(mac=mac, mask='ff-ff-00-00-00-00'), '00:11:*:*:*:*')
    self.assertEqual(f(mac=mac, mask='ff-00-00-00-00-00'), '00:*:*:*:*:*')
    self.assertEqual(f(mac=mac, mask='00-00-00-00-00-00'), '*:*:*:*:*:*')
    self.assertEqual(f(mac=mac, mask=''), '00:11:22:33:44:55')
    self.assertEqual(f(mac=mac, mask='foo'), '00:11:22:33:44:55')
    self.assertEqual(f(mac=mac, mask='123456789'), '00:11:22:33:44:55')

  def testBasicConfig(self):
    dh4p = self.dh4p
    dh4p.Enable = True
    dh4p.MinAddress = '1.1.1.1'
    dh4p.MaxAddress = '2.2.2.2'
    dh4p.DomainName = 'example.com'
    dh4p.DNSServers = '3.3.3.3,4.4.4.4'
    dh4p.X_CATAWAMPUS_ORG_NTPServers = '5.5.5.5,6.6.6.6'
    dh4p.IPRouters = '9.9.9.9'
    self.loop.RunOnce(timeout=1)
    lines = dnsmasq._ReadFileActiveLines(dnsmasq.DNSMASQCONFIG[0])
    # self.assertTrue before remove() to make the test more clear.
    expectedLines = [
        'dhcp-range=1.1.1.1,2.2.2.2,86400\n',
        'domain=example.com\n',
        'dhcp-option=option:router,9.9.9.9\n',
        'dhcp-option=option:ntp-server,5.5.5.5,6.6.6.6\n',
        'dhcp-option=option:dns-server,3.3.3.3,4.4.4.4\n',
    ]
    for expected in expectedLines:
      self.assertTrue(expected in lines)
      lines.remove(expected)
    self.assertEqual(len(lines), 0)
    self.assertTrue(os.path.exists(self.restartfile))

  def testSuppressIdenticalConfig(self):
    """Test that an identical config is not rewritten."""
    dh4p = self.dh4p
    dh4p.Enable = True
    dh4p.MinAddress = '1.1.1.1'
    dh4p.MaxAddress = '2.2.2.2'
    self.loop.RunOnce(timeout=1)
    self.assertTrue(os.path.exists(self.restartfile))
    os.unlink(self.restartfile)
    fs = os.stat(dnsmasq.DNSMASQCONFIG[0])
    dh4p.MaxAddress = '2.2.2.2'
    self.loop.RunOnce(timeout=1)
    fs2 = os.stat(dnsmasq.DNSMASQCONFIG[0])
    self.assertEqual(fs, fs2)
    self.assertFalse(os.path.exists(self.restartfile))

  def testEnableDisable(self):
    dh4p = self.dh4p
    dh4p.Enable = True
    dh4p.MinAddress = '1.1.1.1'
    dh4p.MaxAddress = '2.2.2.2'
    self.assertFalse(os.path.exists(dnsmasq.DNSMASQCONFIG[0]))
    self.loop.RunOnce(timeout=1)
    self.assertTrue(os.path.exists(dnsmasq.DNSMASQCONFIG[0]))
    lines = dnsmasq._ReadFileActiveLines(dnsmasq.DNSMASQCONFIG[0])
    self.assertEqual(lines, ['dhcp-range=1.1.1.1,2.2.2.2,86400\n'])
    dh4p.Enable = False
    self.loop.RunOnce(timeout=1)
    self.assertTrue(os.path.exists(dnsmasq.DNSMASQCONFIG[0]))
    lines = dnsmasq._ReadFileActiveLines(dnsmasq.DNSMASQCONFIG[0])
    self.assertEqual(lines, [])

  def testIncompleteConfig(self):
    dh4p = self.dh4p
    self.loop.RunOnce(timeout=1)
    self.assertFalse(os.path.exists(dnsmasq.DNSMASQCONFIG[0]))
    dh4p.Enable = True
    dh4p.MinAddress = '1.1.1.1'
    self.loop.RunOnce(timeout=1)
    lines = dnsmasq._ReadFileActiveLines(dnsmasq.DNSMASQCONFIG[0])
    self.assertEqual(lines, [])
    dh4p.MaxAddress = '3.3.3.3'
    self.loop.RunOnce(timeout=1)
    lines = dnsmasq._ReadFileActiveLines(dnsmasq.DNSMASQCONFIG[0])
    expected = ['dhcp-range=1.1.1.1,3.3.3.3,86400\n']
    self.assertEqual(expected, lines)

  def testRestartCmdFails(self):
    """'restart dnsmasq' failing should not kill the process."""
    dnsmasq.RESTARTCMD = ['/nonexistent']
    dh4p = self.dh4p
    dh4p.Enable = True
    dh4p.MinAddress = '1.1.1.1'
    dh4p.MaxAddress = '2.2.2.2'
    self.loop.RunOnce(timeout=1)
    # should see a traceback, but not kill the process
    dnsmasq.RESTARTCMD = ['testdata/dnsmasq/restart_fails']
    dh4p.MaxAddress = '2.2.2.3'
    self.loop.RunOnce(timeout=1)
    # should see a traceback, but not kill the process

  def _setConditionalParameters(self, dh4p):
    """Set parameters for the ConditionalConfig test cases."""
    dh4p.Enable = True
    dh4p.MinAddress = '1.1.1.1'
    dh4p.MaxAddress = '2.2.2.2'
    dh4p.DomainName = 'example.com'
    dh4p.DNSServers = '3.3.3.3,4.4.4.4'
    dh4p.X_CATAWAMPUS_ORG_NTPServers = '5.5.5.5,6.6.6.6'
    dh4p.IPRouters = '9.9.9.9'
    dh4p.DNSServers = '8.8.8.8,8.8.4.4'
    h = tr.handle.Handle(dh4p)
    (_, opt) = h.AddExportObject('Option')
    opt.Enable = True
    opt.Tag = 40
    opt.Value = '77756262617775626261'  # 'wubbawubba'
    (_, opt) = h.AddExportObject('Option')
    opt.Enable = False
    opt.Tag = 41
    opt.Value = '776f636b61776f636b61'  # 'wockawocka'
    (_, ip) = h.AddExportObject('StaticAddress')
    ip.Enable = True
    ip.Chaddr = '11:22:33:44:55:66'
    ip.Yiaddr = '1.2.3.4'
    (_, ip) = h.AddExportObject('StaticAddress')
    ip.Enable = False
    ip.Chaddr = '22:33:44:55:66:77'
    ip.Yiaddr = '2.3.4.5'
    (_, ip) = h.AddExportObject('StaticAddress')
    ip.Enable = True
    ip.X_CATAWAMPUS_ORG_ClientID = 'client_id'
    ip.Yiaddr = '3.4.5.6'

  def _checkConditionalResults(self, lines):
    """Check results for the ConditionalConfig test cases."""
    expectedLines = [
        'dhcp-range=tag:test,1.1.1.1,2.2.2.2,86400\n',
        'domain=example.com,1.1.1.1,2.2.2.2\n',
        'dhcp-option=tag:test,option:router,9.9.9.9\n',
        'dhcp-option=tag:test,option:ntp-server,5.5.5.5,6.6.6.6\n',
        'dhcp-option=tag:test,option:dns-server,8.8.8.8,8.8.4.4\n',
        'dhcp-option=tag:test,option:40,wubbawubba\n',
        'dhcp-host=tag:test,11:22:33:44:55:66,1.2.3.4\n',
        'dhcp-host=tag:test,id:client_id,3.4.5.6\n',
    ]
    for expected in expectedLines:
      self.assertTrue(expected in lines)
      lines.remove(expected)

  def testMACConditionalConfig(self):
    dh4p = self.dh4p
    dh4p.Chaddr = '11:22:33:44:55:66'
    dh4p.ChaddrMask = 'ff:ff:ff:00:00:00'
    self._setConditionalParameters(dh4p)
    self.loop.RunOnce(timeout=1)
    lines = dnsmasq._ReadFileActiveLines(dnsmasq.DNSMASQCONFIG[0])
    self.assertTrue('dhcp-host=11:22:33:*:*:*,set:test\n' in lines)
    lines.remove('dhcp-host=11:22:33:*:*:*,set:test\n')
    self._checkConditionalResults(lines)
    self.assertEqual(len(lines), 0)

  def testVendorClassConditionalConfig(self):
    dh4p = self.dh4p
    dh4p.VendorClassID = 'vendorClass'
    self._setConditionalParameters(dh4p)
    self.loop.RunOnce(timeout=1)
    lines = dnsmasq._ReadFileActiveLines(dnsmasq.DNSMASQCONFIG[0])
    self.assertTrue('dhcp-vendorclass=set:test,vendorClass\n' in lines)
    lines.remove('dhcp-vendorclass=set:test,vendorClass\n')
    self._checkConditionalResults(lines)
    self.assertEqual(len(lines), 0)

  def testUserClassConditionalConfig(self):
    dh4p = self.dh4p
    dh4p.UserClassID = 'userClass'
    self._setConditionalParameters(dh4p)
    self.loop.RunOnce(timeout=1)
    lines = dnsmasq._ReadFileActiveLines(dnsmasq.DNSMASQCONFIG[0])
    self.assertTrue('dhcp-userclass=set:test,userClass\n' in lines)
    lines.remove('dhcp-userclass=set:test,userClass\n')
    self._checkConditionalResults(lines)
    self.assertEqual(len(lines), 0)

  def testIPv6DnsServerInConfig(self):
    dh4p = self.dh4p
    dh4p.DNSServers = '3.3.3.3,4.4.4.4'
    # non-IPv4 address in the list
    dns = '3.3.3.3,4.4.4.4,1:2::3'
    self.assertRaises(ValueError, setattr, dh4p, 'DNSServers', dns)

  def testMultipleDhcpHosts(self):
    dh4p = self.dh4p
    h = tr.handle.Handle(dh4p)
    dh4p.Enable = True
    (_, ip) = h.AddExportObject('StaticAddress')
    ip.Enable = True
    ip.Chaddr = '11:22:33:44:55:66'
    ip.Yiaddr = '1.2.3.4'
    (_, ip) = h.AddExportObject('StaticAddress')
    ip.Enable = True
    ip.Chaddr = '22:33:44:55:66:77'
    ip.Yiaddr = '1.2.3.4'
    (_, ip) = h.AddExportObject('StaticAddress')
    ip.Enable = True
    ip.X_CATAWAMPUS_ORG_ClientID = 'cid'
    ip.Yiaddr = '1.2.3.4'

    self.loop.RunOnce(timeout=1)
    lines = dnsmasq._ReadFileActiveLines(dnsmasq.DNSMASQCONFIG[0])
    # self.assertTrue before remove() to make the test more clear.
    e = ['dhcp-host=11:22:33:44:55:66,22:33:44:55:66:77,id:cid,1.2.3.4\n']
    self.assertEqual(e, lines)

  def testStatus(self):
    dh4p = self.dh4p
    dh4p.MinAddress = '1.2.3.4'
    self.assertEqual(dh4p.Status, 'Error_Misconfigured')
    dh4p.MaxAddress = '1.2.3.5'
    self.assertEqual(dh4p.Status, 'Disabled')
    dh4p.Enable = True
    self.assertEqual(dh4p.Status, 'Enabled')
    dh4p.MinAddress = ''
    self.assertEqual(dh4p.Status, 'Error_Misconfigured')

  def testTextConfig(self):
    dnsmasq.DNSMASQCONFIG[0] = 'testdata/dnsmasq/dnsmasq.conf'
    dh4 = dnsmasq.Dhcp4Server()
    expected = 'This is not a real config, silly.'
    self.assertEqual(dh4.X_CATAWAMPUS_ORG_TextConfig, expected)

  def testLeases(self):
    dh4p = self.dh4p
    self.assertEqual(len(dh4p.ClientList), 3)

    client = dh4p.ClientList['1']
    self.assertEqual(client.Chaddr, '00:01:02:03:04:01')
    ipl = client.IPv4AddressList
    self.assertEqual(len(ipl), 1)
    self.assertEqual(ipl['1'].IPAddress, '192.168.1.1')
    self.assertEqual(str(ipl['1'].LeaseTimeRemaining), '2013-11-10 04:16:40')
    self.assertEqual(len(client.OptionList), 1)
    self.assertEqual(client.OptionList['2'].Tag, 12)
    self.assertEqual(client.OptionList['2'].Value, 'host-1')

    client = dh4p.ClientList['2']
    self.assertEqual(client.Chaddr, '00:01:02:03:04:02')
    ipl = client.IPv4AddressList
    self.assertEqual(len(ipl), 1)
    self.assertEqual(ipl['1'].IPAddress, '192.168.1.2')
    self.assertEqual(str(ipl['1'].LeaseTimeRemaining), '2013-11-10 04:33:20')
    self.assertEqual(len(client.OptionList), 2)
    self.assertEqual(client.OptionList['1'].Tag, 61)
    # 'client-id-2' == 636c69656e742d69642d32
    self.assertEqual(client.OptionList['1'].Value, '636c69656e742d69642d32')
    self.assertEqual(client.OptionList['2'].Tag, 12)
    self.assertEqual(client.OptionList['2'].Value, 'host-2')

    client = dh4p.ClientList['3']
    self.assertEqual(client.Chaddr, '00:01:02:03:04:03')
    ipl = client.IPv4AddressList
    self.assertEqual(len(ipl), 1)
    self.assertEqual(ipl['1'].IPAddress, '192.168.1.3')
    self.assertEqual(str(ipl['1'].LeaseTimeRemaining), '2013-11-10 04:50:00')
    self.assertEqual(len(client.OptionList), 1)
    self.assertEqual(client.OptionList['1'].Tag, 61)
    # 'client-id-3' == 636c69656e742d69642d33
    self.assertEqual(client.OptionList['1'].Value, '636c69656e742d69642d33')

  def testDnsmasqLeasesCorrupt(self):
    dnsmasq.DNSMASQLEASES[0] = 'testdata/dnsmasq/leases.corrupt'
    dh4p = self.dh4p
    self.assertEqual(len(dh4p.ClientList), 0)

  def testDnsmasqLeasesMissing(self):
    dnsmasq.DNSMASQLEASES[0] = '/nonexistent'
    dh4p = self.dh4p
    self.assertEqual(len(dh4p.ClientList), 0)


if __name__ == '__main__':
  unittest.main()

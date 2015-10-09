#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
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

"""Unit tests for tr-181 Ethernet.* implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
from tr.wvtest import unittest
import tr.basemodel
import tr.handle
import ethernet
import netdev


BASEETHERNET = tr.basemodel.Device.Ethernet


class EthernetTest(unittest.TestCase):
  """Tests for ethernet.py."""

  def setUp(self):
    self.old_PROC_NET_DEV = netdev.PROC_NET_DEV
    self.old_PYNETIFCONF = ethernet.PYNETIFCONF
    netdev.PROC_NET_DEV = 'testdata/ethernet/net_dev'
    ethernet.PYNETIFCONF = MockPynet
    MockPynet.reset()

  def tearDown(self):
    netdev.PROC_NET_DEV = self.old_PROC_NET_DEV
    ethernet.PYNETIFCONF = self.old_PYNETIFCONF

  def testInterfaceStatsGood(self):
    eth = ethernet.EthernetInterfaceStatsLinux26('foo0')
    tr.handle.ValidateExports(eth)
    # only a sanity check. Extensive tests in netdev_test.py
    self.assertEqual(eth.PacketsSent, 10)

  def _CheckEthernetInterfaceParameters(self, ifname, upstream, eth, pynet):
    if pynet.v_duplex is None:
      self.assertEqual(eth.DuplexMode, 'Unknown')
    elif pynet.v_duplex:
      self.assertEqual(eth.DuplexMode, 'Full')
    else:
      self.assertEqual(eth.DuplexMode, 'Half')
    self.assertEqual(eth.Enable, True)
    self.assertEqual(eth.LastChange, '0001-01-01T00:00:00Z')
    self.assertFalse(eth.LowerLayers)
    if hasattr(pynet, 'v_mac'):
      self.assertEqual(eth.MACAddress, pynet.v_mac)
    self.assertEqual(eth.MaxBitRate, pynet.v_speed)
    self.assertEqual(eth.Name, ifname)
    self.assertEqual(eth.Upstream, upstream)
    self.assertEqual(eth.X_CATAWAMPUS_ORG_ActualBitRate, eth.MaxBitRate)
    self.assertEqual(eth.X_CATAWAMPUS_ORG_ActualDuplexMode, eth.DuplexMode)

  def testValidateExports(self):
    eth = ethernet.EthernetInterfaceLinux26('foo0')
    tr.handle.ValidateExports(eth)

  def testInterfaceGood(self):
    upstream = False

    eth = ethernet.EthernetInterfaceLinux26('foo0')
    self._CheckEthernetInterfaceParameters('foo0', upstream, eth, MockPynet)

    eth = ethernet.EthernetInterfaceLinux26('foo0')
    self._CheckEthernetInterfaceParameters('foo0', upstream, eth, MockPynet)

    MockPynet.v_is_up = False
    eth = ethernet.EthernetInterfaceLinux26('foo0')
    self._CheckEthernetInterfaceParameters('foo0', upstream, eth, MockPynet)

    MockPynet.v_duplex = False
    eth = ethernet.EthernetInterfaceLinux26('foo0')
    self._CheckEthernetInterfaceParameters('foo0', upstream, eth, MockPynet)

    MockPynet.v_auto = False
    eth = ethernet.EthernetInterfaceLinux26('foo0')
    self._CheckEthernetInterfaceParameters('foo0', upstream, eth, MockPynet)

    MockPynet.v_link_up = False
    eth = ethernet.EthernetInterfaceLinux26('foo0')
    self._CheckEthernetInterfaceParameters('foo0', upstream, eth, MockPynet)

  def testIOError(self):
    ethernet.PYNETIFCONF = MockIOErrorPynet

    upstream = False
    eth = ethernet.EthernetInterfaceLinux26('foo0')
    self._CheckEthernetInterfaceParameters('foo0', upstream, eth,
                                           MockIOErrorPynet)

  def testDiscardFramePresence(self):
    # Content of DiscardFrameCnts is tested in netdev_test.py.
    d1 = 'X_CATAWAMPUS-ORG_DiscardFrameCnts'
    d2 = 'X_CATAWAMPUS-ORG_DiscardPacketsReceivedHipri'
    eth = ethernet.EthernetInterfaceLinux26('foo0', qfiles=None)
    self.assertFalse(tr.handle.Handle.IsValidExport(eth.Stats, d1))
    self.assertFalse(tr.handle.Handle.IsValidExport(eth.Stats, d2))

    qfiles = 'testdata/sysfs/eth0/bcmgenet_discard_cnt_q%d'
    eth = ethernet.EthernetInterfaceLinux26('foo0', qfiles=qfiles, numq=2)
    self.assertTrue(tr.handle.Handle.IsValidExport(eth.Stats, d1))
    self.assertTrue(tr.handle.Handle.IsValidExport(eth.Stats, d2))

  def testStatus(self):
    eth = ethernet.EthernetInterfaceLinux26('foo0')
    MockPynet.v_is_up = False
    MockPynet.v_link_up = True
    self.assertEqual(eth.Status, 'Down')
    MockPynet.v_is_up = True
    MockPynet.v_link_up = True
    self.assertEqual(eth.Status, 'Up')
    MockPynet.v_is_up = True
    MockPynet.v_link_up = False
    self.assertEqual(eth.Status, 'Down')

  def testStatusFcn(self):
    eth = ethernet.EthernetInterfaceLinux26(
        'foo0', status_fcn=lambda: None)
    MockPynet.v_is_up = False
    self.assertEqual(eth.Status, 'Down')
    MockPynet.v_is_up = True
    MockPynet.v_link_up = True
    self.assertEqual(eth.Status, 'Up')

    eth = ethernet.EthernetInterfaceLinux26(
        'foo0', status_fcn=lambda: 'Forced')
    MockPynet.v_is_up = False
    self.assertEqual(eth.Status, 'Forced')
    MockPynet.v_is_up = True
    self.assertEqual(eth.Status, 'Forced')


class MockPynet(object):
  v_is_up = True
  v_mac = '00:11:22:33:44:55'
  v_speed = 1000
  v_duplex = True
  v_auto = True
  v_link_up = True

  @staticmethod
  def reset():
    MockPynet.v_is_up = True
    MockPynet.v_mac = '00:11:22:33:44:55'
    MockPynet.v_speed = 1000
    MockPynet.v_duplex = True
    MockPynet.v_auto = True
    MockPynet.v_link_up = True

  def __init__(self, ifname):
    self.ifname = ifname

  def is_up(self):
    return self.v_is_up

  def get_mac(self):
    return self.v_mac

  def get_link_info(self):
    return (self.v_speed, self.v_duplex, self.v_auto, self.v_link_up)


class MockIOErrorPynet(object):
  """A mock pynetlinux.ifconfig.Interface that raises IOError on every call."""

  v_speed = 0
  v_duplex = None
  v_auto = None
  v_link_up = None

  def __init__(self, ifname):
    self.ifname = ifname

  def is_up(self):
    raise IOError('mock IOError')

  def get_mac(self):
    raise IOError('mock IOError')

  def get_link_info(self):
    raise IOError('mock IOError')


if __name__ == '__main__':
  unittest.main()

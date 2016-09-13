#!/usr/bin/python
# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Unit tests for IpDiagIperf3 implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
from tr.wvtest import unittest
import tr.handle
import tr.mainloop
import ip_diag_iperf3


class DiagIperf3Test(unittest.TestCase):
  """Tests for ip_diag_iperf3.py."""

  def setUp(self):
    super(DiagIperf3Test, self).setUp()
    self.old_IPERF3 = ip_diag_iperf3.IPERF3
    ip_diag_iperf3.IPERF3[0] = 'testdata/ip_diag_iperf3/iperf3'
    self.loop = tr.mainloop.MainLoop()

  def tearDown(self):
    super(DiagIperf3Test, self).tearDown()
    ip_diag_iperf3.IPERF3 = self.old_IPERF3

  def testValidateExports(self):
    iperf3 = ip_diag_iperf3.DiagIperf3()
    tr.handle.ValidateExports(iperf3)

  def _WaitUntilCompleted(self, iperf3):
    iperf3.DiagnosticsState = 'Requested'
    while iperf3.DiagnosticsState == 'Requested':
      self.loop.RunOnce(timeout=5)

  def testSimple(self):
    iperf3 = ip_diag_iperf3.DiagIperf3()
    iperf3.Host = 'hostname'
    self._WaitUntilCompleted(iperf3)
    self.assertEqual(iperf3.DiagnosticsState, 'Complete')
    self.assertTrue('hostname' in iperf3.Result)
    self.assertTrue('iperf3:' in iperf3.Result)

  def testIPv4AddressPing(self):
    iperf3 = ip_diag_iperf3.DiagIperf3()
    iperf3.Host = '8.8.8.8'
    self._WaitUntilCompleted(iperf3)
    self.assertEqual(iperf3.DiagnosticsState, 'Complete')
    self.assertTrue('8.8.8.8' in iperf3.Result)
    self.assertTrue('--version4' in iperf3.Result)
    self.assertTrue('iperf3:' in iperf3.Result)

  def testIPv6AddressPing(self):
    iperf3 = ip_diag_iperf3.DiagIperf3()
    iperf3.Host = '1::1'
    self._WaitUntilCompleted(iperf3)
    self.assertEqual(iperf3.DiagnosticsState, 'Complete')
    self.assertTrue('1::1' in iperf3.Result)
    self.assertTrue('--version6' in iperf3.Result)
    self.assertTrue('iperf3:' in iperf3.Result)

  def testDscp(self):
    iperf3 = ip_diag_iperf3.DiagIperf3()
    iperf3.DSCP = 11
    iperf3.Host = 'example.com'
    self._WaitUntilCompleted(iperf3)
    self.assertEqual(iperf3.DiagnosticsState, 'Complete')
    self.assertTrue('--tos 11' in iperf3.Result)

  def testExtraArguments(self):
    iperf3 = ip_diag_iperf3.DiagIperf3()
    iperf3.ExtraArguments = '--extra --arguments'
    iperf3.Host = 'example.com'
    self._WaitUntilCompleted(iperf3)
    self.assertEqual(iperf3.DiagnosticsState, 'Complete')
    self.assertTrue('--extra --arguments' in iperf3.Result)


if __name__ == '__main__':
  unittest.main()

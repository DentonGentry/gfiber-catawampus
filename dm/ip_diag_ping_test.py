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

"""Unit tests for DiagPing implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
from tr.wvtest import unittest
import tr.handle
import tr.mainloop
import ip_diag_ping


class DiagPingTest(unittest.TestCase):
  """Tests for ip_diag_ping.py."""

  def setUp(self):
    super(DiagPingTest, self).setUp()
    self.old_PING4 = ip_diag_ping.PING4
    self.old_PING6 = ip_diag_ping.PING6
    ip_diag_ping.PING4[0] = 'testdata/ip_diag_ping/ping4'
    ip_diag_ping.PING6[0] = 'testdata/ip_diag_ping/ping6'
    self.loop = tr.mainloop.MainLoop()

  def tearDown(self):
    super(DiagPingTest, self).tearDown()
    ip_diag_ping.PING4 = self.old_PING4

  def testValidateExports(self):
    ping = ip_diag_ping.DiagPing()
    tr.handle.ValidateExports(ping)

  def _WaitUntilCompleted(self, ping):
    ping.DiagnosticsState = 'Requested'
    while ping.DiagnosticsState == 'Requested':
      self.loop.RunOnce(timeout=5)

  def testSimplePing(self):
    ping = ip_diag_ping.DiagPing()
    ping.Host = '8.8.8.8'
    self._WaitUntilCompleted(ping)
    self.assertEqual(ping.DiagnosticsState, 'Complete')
    self.assertTrue('8.8.8.8' in ping.Result)
    self.assertTrue('ping4:' in ping.Result)

  def testIPv6AddressPing(self):
    ping = ip_diag_ping.DiagPing()
    ping.Host = '1::1'
    self._WaitUntilCompleted(ping)
    self.assertEqual(ping.DiagnosticsState, 'Complete')
    self.assertTrue('1::1' in ping.Result)
    self.assertTrue('ping6:' in ping.Result)

  def testHostnamePing(self):
    ping = ip_diag_ping.DiagPing()
    ping.Host = 'foo.bar.com'
    self._WaitUntilCompleted(ping)
    self.assertEqual(ping.DiagnosticsState, 'Complete')
    self.assertTrue('foo.bar.com' in ping.Result)
    self.assertTrue('ping4:' in ping.Result)
    ping.ProtocolVersion = 'IPv6'
    ping.Host = 'foo.bar.com'
    self._WaitUntilCompleted(ping)
    self.assertEqual(ping.DiagnosticsState, 'Complete')
    self.assertTrue('foo.bar.com' in ping.Result)
    self.assertTrue('ping6:' in ping.Result)

  def testNumberOfRepetitions(self):
    ping = ip_diag_ping.DiagPing()
    ping.NumberOfRepetitions = 100
    ping.Host = 'foo.bar.com'
    self._WaitUntilCompleted(ping)
    self.assertEqual(ping.DiagnosticsState, 'Complete')
    self.assertTrue('-c 100 ' in ping.Result)

  def testTimeout(self):
    ping = ip_diag_ping.DiagPing()
    ping.Timeout = 10
    ping.Host = 'foo.bar.com'
    self._WaitUntilCompleted(ping)
    self.assertEqual(ping.DiagnosticsState, 'Complete')
    self.assertTrue('-w 10 ' in ping.Result)

  def testDscp(self):
    ping = ip_diag_ping.DiagPing()
    ping.DSCP = 11
    ping.Host = 'foo.bar.com'
    self._WaitUntilCompleted(ping)
    self.assertEqual(ping.DiagnosticsState, 'Complete')
    self.assertTrue('-Q 11 ' in ping.Result)


if __name__ == '__main__':
  unittest.main()

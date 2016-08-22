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

"""Unit tests for TraceRoute implementation."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import google3
from tr.wvtest import unittest
import tr.handle
import tr.mainloop
import traceroute


class TraceRouteTest(unittest.TestCase):
  """Tests for traceroute.py."""

  def setUp(self):
    self.loop = tr.mainloop.MainLoop()
    traceroute.TRACEROUTE = 'testdata/traceroute/traceroute'
    traceroute.TRACEROUTE6 = 'testdata/traceroute/traceroute6'

  def _DoTrace(self, trace, hostname, maxhops):
    trace.Host = hostname
    trace.MaxHopCount = maxhops
    trace.DiagnosticsState = 'Requested'
    while trace.DiagnosticsState == 'Requested':
      self.loop.RunOnce(timeout=5)

  def testValidateExports(self):
    trace = traceroute.TraceRoute(self.loop.ioloop)
    tr.handle.ValidateExports(trace)

  def testAlternateTraceRouteOutputFormat(self):
    trace = traceroute.TraceRoute(self.loop.ioloop)
    self._DoTrace(trace, 'shakespeare', 30)
    self.assertEqual(len(trace.RouteHopsList), 6)
    self.assertEqual(trace.RouteHopsNumberOfEntries, 6)
    self.assertEqual(trace.RouteHopsList[1].Host, 'the.fault')
    self.assertEqual(trace.RouteHopsList[2].Host, 'dear.brutus')
    self.assertEqual(trace.RouteHopsList[3].Host, 'is.not')
    self.assertEqual(trace.RouteHopsList[4].Host, 'in.our')
    self.assertEqual(trace.RouteHopsList[5].Host, 'stars.but')
    self.assertEqual(trace.RouteHopsList[6].Host, 'in.ourselves')
    self.assertEqual(trace.RouteHopsList[1].HostAddress, '192.168.1.1')
    self.assertEqual(trace.RouteHopsList[2].HostAddress, '15.99.15.99')
    self.assertEqual(trace.RouteHopsList[3].HostAddress, '20.20.20.20')
    self.assertEqual(trace.RouteHopsList[4].HostAddress, '40.40.40.40')
    self.assertEqual(trace.RouteHopsList[5].HostAddress, '60.60.60.60')
    self.assertEqual(trace.RouteHopsList[6].HostAddress, '80.80.80.80')
    self.assertEqual(trace.DiagnosticsState, 'Complete')

  def testTraceRouteLocalhost(self):
    trace = traceroute.TraceRoute(self.loop.ioloop)
    self._DoTrace(trace, '127.0.0.1', 1)
    self.assertEqual(len(trace.RouteHopsList), 1)
    self.assertEqual(trace.RouteHopsNumberOfEntries, 1)
    self.assertEqual(trace.RouteHopsList[1].Host, 'localhost')
    self.assertEqual(trace.RouteHopsList[1].HostAddress, '127.0.0.1')
    self.assertEqual(trace.DiagnosticsState, 'Error_MaxHopCountExceeded')

    self._DoTrace(trace, '::1', 2)
    self.assertEqual(len(trace.RouteHopsList), 1)
    self.assertEqual(trace.RouteHopsNumberOfEntries, 1)
    self.assertEqual(trace.RouteHopsList[1].Host, 'localhost')
    self.assertEqual(trace.RouteHopsList[1].HostAddress, '::1')
    self.assertEqual(trace.DiagnosticsState, 'Complete')

  def testTraceRouteCannotResolve(self):
    trace = traceroute.TraceRoute(self.loop.ioloop)
    self._DoTrace(trace, 'this-name-does-not-exist', 30)
    self.assertEqual(len(trace.RouteHopsList), 0)
    self.assertEqual(trace.DiagnosticsState, 'Error_CannotResolveHostName')
    self.assertEqual(trace.RouteHopsNumberOfEntries, 0)
    self.assertEqual(trace.ResponseTime, 0)

  def testATaleOfTwoCities(self):
    trace = traceroute.TraceRoute(self.loop.ioloop)
    self._DoTrace(trace, 'of.times', 30)
    self.assertEqual(len(trace.RouteHopsList), 6)
    self.assertEqual(trace.RouteHopsNumberOfEntries, 6)
    self.assertEqual(trace.RouteHopsList[1].Host, 'it.was')
    self.assertEqual(trace.RouteHopsList[2].Host, 'the.best')
    self.assertEqual(trace.RouteHopsList[3].Host, 'of.times')
    self.assertEqual(trace.RouteHopsList[4].Host, 'it.was')
    self.assertEqual(trace.RouteHopsList[5].Host, 'the.worst')
    self.assertEqual(trace.RouteHopsList[6].Host, 'of.times')
    self.assertEqual(trace.RouteHopsList[1].HostAddress, '12.34.56.78')
    self.assertEqual(trace.RouteHopsList[2].HostAddress, '34.56.78.90')
    self.assertEqual(trace.RouteHopsList[3].HostAddress, '56.78.90.12')
    self.assertEqual(trace.RouteHopsList[4].HostAddress, '78.90.12.34')
    self.assertEqual(trace.RouteHopsList[5].HostAddress, '90.12.34.56')
    self.assertEqual(trace.RouteHopsList[6].HostAddress, '12.34.56.79')
    self.assertEqual(trace.DiagnosticsState, 'Complete')
    self.assertEqual(trace.ResponseTime, int(1.277))

  def testATaleOfTwoCitiesIPv6(self):
    trace = traceroute.TraceRoute(self.loop.ioloop)
    trace.IPVersion = 'IPv6'
    self._DoTrace(trace, 'of.times', 30)
    self.assertEqual(len(trace.RouteHopsList), 6)
    self.assertEqual(trace.RouteHopsNumberOfEntries, 6)
    self.assertEqual(trace.RouteHopsList[1].Host, 'it.was')
    self.assertEqual(trace.RouteHopsList[2].Host, 'the.best')
    self.assertEqual(trace.RouteHopsList[3].Host, 'of.times')
    self.assertEqual(trace.RouteHopsList[4].Host, 'it.was')
    self.assertEqual(trace.RouteHopsList[5].Host, 'the.worst')
    self.assertEqual(trace.RouteHopsList[6].Host, 'of.times')
    self.assertEqual(
        trace.RouteHopsList[1].HostAddress, '1000:1000:1000:1001::1')
    self.assertEqual(
        trace.RouteHopsList[2].HostAddress, '1000:1000:1000:1002::')
    self.assertEqual(
        trace.RouteHopsList[3].HostAddress, '1000:1000:1000:1003::')
    self.assertEqual(
        trace.RouteHopsList[4].HostAddress,
        '1000:1000:1000:1004:1e:1000:0:23')
    self.assertEqual(
        trace.RouteHopsList[5].HostAddress, '1000:1000:1000:1005::')
    self.assertEqual(
        trace.RouteHopsList[6].HostAddress,
        '1000:1000:1000:1006:1e:1000:0:21')
    self.assertEqual(trace.DiagnosticsState, 'Complete')
    # rounding up the last RTT in the trace
    self.assertEqual(trace.ResponseTime, 7)

  def testTraceIPv6Address(self):
    trace = traceroute.TraceRoute(self.loop.ioloop)
    self._DoTrace(trace, '1000:1000:1000:1000::1000', 30)
    self.assertEqual(trace.RouteHopsNumberOfEntries, 6)
    # spot-checkthat this is the IPv6 trace
    self.assertEqual(
        trace.RouteHopsList[1].HostAddress, '1000:1000:1000:1001::1')
    self.assertEqual(trace.DiagnosticsState, 'Complete')

if __name__ == '__main__':
  unittest.main()

#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for TraceRoute implementation."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import unittest
import _fix_path  #pylint: disable-msg=W0611
import tr.mainloop
import traceroute


class TraceRouteTest(unittest.TestCase):
  """Tests for traceroute.py."""

  def _DoTrace(self, loop, trace, hostname, maxhops):
    trace.Host = hostname
    trace.MaxHopCount = maxhops
    trace.DiagnosticsState = 'Requested'
    while trace.DiagnosticsState == 'Requested':
      loop.RunOnce(timeout=5)

  def testTraceRoute(self):
    loop = tr.mainloop.MainLoop()
    trace = traceroute.TraceRoute(loop)

    self._DoTrace(loop, trace, '127.0.0.1', 1)
    self.assertEqual(len(trace.RouteHopsList), 1)
    self.assertEqual(trace.RouteHopsList[1].Host, 'localhost')
    self.assertEqual(trace.RouteHopsList[1].HostAddress, '127.0.0.1')
    self.assertEqual(trace.DiagnosticsState, 'Error_MaxHopCountExceeded')

    self._DoTrace(loop, trace, '::1', 2)
    self.assertEqual(len(trace.RouteHopsList), 1)
    self.assertEqual(trace.RouteHopsList[1].Host, 'localhost')
    self.assertEqual(trace.RouteHopsList[1].HostAddress, '::1')
    self.assertEqual(trace.DiagnosticsState, 'Complete')

    self._DoTrace(loop, trace, 'this-name-does-not-exist', 30)
    self.assertEqual(len(trace.RouteHopsList), 0)
    self.assertEqual(trace.DiagnosticsState, 'Error_CannotResolveHostName')

    self._DoTrace(loop, trace, 'google.com', 30)
    self.assertTrue(len(trace.RouteHopsList) > 1)
    self.assertEqual(trace.DiagnosticsState, 'Complete')


if __name__ == '__main__':
  unittest.main()

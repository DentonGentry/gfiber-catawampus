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

# TR-069 has mandatory attribute names that don't comply with policy
# pylint: disable-msg=C6409
# pylint: disable-msg=W0404
#
"""An implementation of Device.IP.Diagnostics.TraceRoute.

Requires a traceroute binary, handles either the LBL traceroute
bundled with many Linux distributions of the new traceroute from
http://traceroute.sourceforge.net/
"""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import os
import re
import subprocess
import sys
import google3
import tornado.ioloop
import tr.core
import tr.tr181_v2_6
import tr.types


BASE_TRACEROUTE = tr.tr181_v2_6.Device_v2_6.Device.IP.Diagnostics.TraceRoute
MIN_PACKET_SIZE = 52  # from MacOS; Linux can apparently go smaller?
TRACEROUTE = 'traceroute'
TRACEROUTE6 = 'traceroute6'


class State(object):
  """Possible values for Device.IP.Diagnostics.TraceRoute.DiagnosticsState."""
  NONE = 'None'
  REQUESTED = 'Requested'
  COMPLETE = 'Complete'
  ERROR_CANNOT_RESOLVE_HOSTNAME = 'Error_CannotResolveHostName'
  ERROR_MAX_HOP_COUNT_EXCEEDED = 'Error_MaxHopCountExceeded'


class TraceRoute(BASE_TRACEROUTE):
  """Implementation of the TraceRoute object from TR-181."""
  DSCP = tr.types.Unsigned(0)
  NumberOfTries = tr.types.Unsigned(3)
  Timeout = tr.types.Unsigned(5000)   # milliseconds
  DataBlockSize = tr.types.Unsigned(38)
  MaxHopCount = tr.types.Unsigned(30)

  def __init__(self, ioloop=None):
    super(TraceRoute, self).__init__()
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.Unexport('Interface')
    self.subproc = None
    self.error = None
    self.buffer = ''
    self.Host = None
    self.response_time = 0
    self.RouteHopsList = {}

  @property
  def RouteHopsNumberOfEntries(self):
    return len(self.RouteHopsList)

  @property
  def ResponseTime(self):
    if self.error:
      return 0
    return self.response_time

  def _ClearHops(self):
    self.RouteHopsList = {}

  def _AddHop(self, hop, ipaddr, hostname, icmp_error, rttimes):
    print 'addhop: %r %r %r %r' % (hostname, ipaddr, icmp_error, rttimes)
    self.RouteHopsList[int(hop)] = self.RouteHops(Host=hostname,
                                                  HostAddress=ipaddr,
                                                  ErrorCode=icmp_error,
                                                  RTTimes=rttimes)
    if rttimes:
      self.response_time = sum(rttimes)/len(rttimes)
    if int(hop) >= int(self.MaxHopCount):
      self.error = State.ERROR_MAX_HOP_COUNT_EXCEEDED

  def _GetState(self):
    if self.subproc:
      return State.REQUESTED
    elif self.error:
      return self.error
    elif self.RouteHopsList:
      return State.COMPLETE
    else:
      return State.NONE

  def _SetState(self, value):
    if value != State.REQUESTED:
      raise ValueError('DiagnosticsState can only be set to "Requested"')
    self._StartProc()

  # pylint: disable-msg=W1001
  DiagnosticsState = property(_GetState, _SetState)

  def _EndProc(self):
    print 'traceroute finished.'
    if self.subproc:
      self.ioloop.remove_handler(self.subproc.stdout.fileno())
      if self.subproc.poll() is None:
        self.subproc.kill()
      rv = self.subproc.poll()
      print 'traceroute: return code was %d' % rv
      if rv == 2 or not self.RouteHopsList:
        self.error = State.ERROR_CANNOT_RESOLVE_HOSTNAME
      self.subproc = None

  def _StartProc(self):
    self._EndProc()
    self._ClearHops()
    self.error = None
    self.response_time = 0
    print 'traceroute starting.'
    if not self.Host:
      raise ValueError('TraceRoute.Host is not set')
    if ':' in self.Host:
      # IPv6
      argv_base = [TRACEROUTE6]
      if sys.platform == 'darwin':
        argv_base += ['-l']  # tell MacOS traceroute6 to include IP addr
    else:
      # assume IPv4
      argv_base = [TRACEROUTE]
    argv = argv_base + ['-m', str(int(self.MaxHopCount)),
                        '-q', str(int(self.NumberOfTries)),
                        '-w', str(int(self.Timeout)/1000)]
    if self.DSCP:
      argv += ['-t', str(int(self.DSCP))]
    argv += [self.Host, str(max(MIN_PACKET_SIZE, int(self.DataBlockSize)))]
    print '  %r' % argv
    self.subproc = subprocess.Popen(argv,
                                    stdout=subprocess.PIPE)
    self.ioloop.add_handler(self.subproc.stdout.fileno(),
                            self._GotData,
                            self.ioloop.READ)

  # pylint: disable-msg=W0613
  def _GotData(self, fd, events):
    data = os.read(fd, 4096)
    if not data:
      self._EndProc()
    else:
      self.buffer += data
      while '\n' in self.buffer:
        before, after = self.buffer.split('\n', 1)
        self.buffer = after
        self._GotLine(before)

  def _GotLine(self, line):
    # TODO(apenwarr): find out how traceroute reports host-unreachable/etc
    # TODO(apenwarr): check that traceroute output is same on OpenWRT
    print 'traceroute line: %r' % (line,)
    g = re.match(r'^\s*(\d+)\s+(\S+) \(([\d:.]+)\)((\s+[\d.]+ ms)+)', line)
    if g:
      hop = g.group(1)
      hostname = g.group(2)
      ipaddr = g.group(3)
      times = g.group(4)
      timelist = re.findall(r'\s+([\d.]+) ms', times)
      self._AddHop(hop, ipaddr, hostname, icmp_error=0,
                   rttimes=[int(float(t)) for t in timelist])
    g = re.match(r'^\s*(\d+)\s+\* \* \*', line)
    if g:
      hop = g.group(1)
      self._AddHop(hop, None, '*', icmp_error=0, rttimes=[])

if __name__ == '__main__':
  print tr.core.DumpSchema(TraceRoute(None))

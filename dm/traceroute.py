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
# pylint:disable=invalid-name
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
import tr.basemodel
import tr.handle
import tr.mainloop
import tr.cwmptypes


BASE_TRACEROUTE = tr.basemodel.Device.IP.Diagnostics.TraceRoute
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
  DataBlockSize = tr.cwmptypes.Unsigned(38)
  DSCP = tr.cwmptypes.Unsigned(0)
  IPVersion = tr.cwmptypes.Enum(
      ['Unspecified', 'IPv4', 'IPv6'], init='Unspecified')
  MaxHopCount = tr.cwmptypes.Unsigned(30)
  NumberOfTries = tr.cwmptypes.Unsigned(3)
  RouteHops = tr.core.Extensible(BASE_TRACEROUTE.RouteHops)
  RouteHopsNumberOfEntries = tr.cwmptypes.NumberOf('RouteHopsList')
  Timeout = tr.cwmptypes.Unsigned(5000)   # milliseconds

  def __init__(self, ioloop=None):
    super(TraceRoute, self).__init__()
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.Unexport(['Interface'])
    self.subproc = None
    self.error = None
    self.buffer = ''
    self.Host = None
    self.response_time = 0
    self.requested = False
    self.RouteHopsList = {}

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
      self.response_time = sum(rttimes) / len(rttimes)
    if int(hop) >= int(self.MaxHopCount):
      self.error = State.ERROR_MAX_HOP_COUNT_EXCEEDED

  def _GetState(self):
    if self.requested or self.subproc:
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
    self.requested = True
    self._StartProc()

  DiagnosticsState = property(_GetState, _SetState)

  def _EndProc(self):
    print 'traceroute finished.'
    if self.subproc:
      self.ioloop.remove_handler(self.subproc.stdout.fileno())
      if self.subproc.poll() is None:
        self.subproc.kill()
      rv = self.subproc.wait()
      print 'traceroute: return code was %d' % rv
      if rv == 2 or not self.RouteHopsList:
        self.error = State.ERROR_CANNOT_RESOLVE_HOSTNAME
      self.subproc = None

  @tr.mainloop.WaitUntilIdle
  def _StartProc(self):
    self._EndProc()
    self._ClearHops()
    self.error = None
    self.response_time = 0
    self.requested = False
    print 'traceroute starting.'
    if not self.Host:
      raise ValueError('TraceRoute.Host is not set')
    if tr.helpers.IsIP6Addr(self.Host) or self.IPVersion == 'IPv6':
      argv_base = [TRACEROUTE6]
      if sys.platform == 'darwin':
        argv_base += ['-l']  # tell MacOS traceroute6 to include IP addr
    else:
      # hostnames are looked up via IPv4
      argv_base = [TRACEROUTE]
    argv = argv_base + ['-m', str(int(self.MaxHopCount)),
                        '-q', str(int(self.NumberOfTries)),
                        '-w', str(int(self.Timeout) / 1000)]
    if self.DSCP:
      argv += ['-t', str(int(self.DSCP))]
    argv += [self.Host, str(max(MIN_PACKET_SIZE, int(self.DataBlockSize)))]
    print '  %r' % argv
    self.subproc = subprocess.Popen(argv,
                                    stdout=subprocess.PIPE, close_fds=True)
    self.ioloop.add_handler(self.subproc.stdout.fileno(),
                            self._GotData,
                            self.ioloop.READ)

  # pylint:disable=unused-argument
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
    print 'traceroute line: %r' % (line,)
    g = (
        re.match(
            r'^\s*(\d+)\s+(\S+) \(\s*([\da-fA-F:.]+)\)((\s+[\d.]+ ms)+)',
            line))
    if g:
      hop = g.group(1)
      hostname = g.group(2)
      ipaddr = g.group(3)
      times = g.group(4)
      timelist = re.findall(r'\s+([\d.]+) ms', times)
      self._AddHop(hop, ipaddr, hostname, icmp_error=0,
                   rttimes=[int(round(float(t))) for t in timelist])
    g = re.match(r'^\s*(\d+)\s+\* \* \*', line)
    if g:
      hop = g.group(1)
      self._AddHop(hop, None, '*', icmp_error=0, rttimes=[])

if __name__ == '__main__':
  print tr.handle.DumpSchema(TraceRoute(None))

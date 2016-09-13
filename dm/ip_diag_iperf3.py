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

# TR-069 has mandatory attribute names that don't comply with policy
# pylint:disable=invalid-name
#
"""Device.X_CATAWAMPUS-ORG.Iperf3.
"""

import os
import subprocess
import google3
import tornado.ioloop
import tr.basemodel
import tr.helpers
import tr.mainloop
import tr.cwmptypes


CATA181IPERF3 = tr.basemodel.Device.X_CATAWAMPUS_ORG.Iperf3
IPERF3 = ['iperf3']


class DiagIperf3(CATA181IPERF3):
  """Implementation of the Iperf3 vendor extension for TR-181."""
  ExtraArguments = tr.cwmptypes.String('')
  ProtocolVersion = tr.cwmptypes.Enum(
      ['Unspecified', 'IPv4', 'IPv6'], init='Unspecified')
  DSCP = tr.cwmptypes.Unsigned(0)
  Host = tr.cwmptypes.String('')
  Result = tr.cwmptypes.String('')

  def __init__(self, ioloop=None):
    super(DiagIperf3, self).__init__()
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.subproc = None
    self.requested = False

  def _GetState(self):
    if self.requested or self.subproc:
      return 'Requested'
    elif self.Result:
      return 'Complete'
    else:
      return 'None'

  def _SetState(self, value):
    if value == 'Requested':
      self.requested = True
      self._StartProc()
    elif value == 'None':
      self.requested = False
      self._EndProc()
    else:
      raise ValueError('Invalid DiagnosticsState, only "Requested" or "None"')

  DiagnosticsState = property(_GetState, _SetState)

  @tr.mainloop.WaitUntilIdle
  def _StartProc(self):
    self._EndProc()
    self.requested = False
    print 'iperf3 diagnostic starting.'

    cmd = list(IPERF3)
    if self.ProtocolVersion == 'IPv6' or tr.helpers.IsIP6Addr(self.Host):
      cmd.extend(['--version6'])
    elif self.ProtocolVersion == 'IPv4' or tr.helpers.IsIP4Addr(self.Host):
      cmd.extend(['--version4'])

    if self.DSCP and self.DSCP < 64:
      cmd.extend(['--tos', str(self.DSCP)])

    if self.Host:
      cmd.extend(['-c', str(self.Host)])
    else:
      cmd.extend(['-s'])

    if self.ExtraArguments:
      cmd.extend(self.ExtraArguments.split())

    self.Result = ' '.join(cmd) + '\n'
    print '  %r' % cmd
    self.subproc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
    self.ioloop.add_handler(self.subproc.stdout.fileno(),
                            self._GotData, self.ioloop.READ)

  def _GotData(self, fd, unused_events):
    data = os.read(fd, 32768)
    if not data:
      self._EndProc()
    else:
      self.Result += data

  def _EndProc(self):
    print 'iperf3 diagnostic finished.'
    if self.subproc:
      self.ioloop.remove_handler(self.subproc.stdout.fileno())
      if self.subproc.poll() is None:
        self.subproc.kill()
      self.subproc = None

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
"""Device.X_CATAWAMPUS-ORG.Ping.
"""

import os
import subprocess
import google3
import tornado.ioloop
import tr.basemodel
import tr.helpers
import tr.mainloop
import tr.cwmptypes


CATA181PING = tr.basemodel.Device.X_CATAWAMPUS_ORG.Ping
PING4 = ['ping']
PING6 = ['ping6']


class DiagPing(CATA181PING):
  """Implementation of the Ping vendor extension for TR-181."""
  ProtocolVersion = tr.cwmptypes.Enum(
      ['Unspecified', 'IPv4', 'IPv6'], init='Unspecified')
  DSCP = tr.cwmptypes.Unsigned(0)
  Host = tr.cwmptypes.String('')
  NumberOfRepetitions = tr.cwmptypes.Unsigned(5)
  Result = tr.cwmptypes.String('')
  Timeout = tr.cwmptypes.Unsigned(5)

  def __init__(self, ioloop=None):
    super(DiagPing, self).__init__()
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
    if value != 'Requested':
      raise ValueError('DiagnosticsState can only be set to "Requested"')
    self.requested = True
    self._StartProc()

  DiagnosticsState = property(_GetState, _SetState)

  @tr.mainloop.WaitUntilIdle
  def _StartProc(self):
    self._EndProc()
    self.requested = False
    print 'ping diagnostic starting.'

    if self.ProtocolVersion == 'IPv6' or tr.helpers.IsIP6Addr(self.Host):
      cmd = list(PING6)
    else:
      cmd = list(PING4)
    cmd += ['-c', str(self.NumberOfRepetitions)]
    cmd += ['-i', '0.1']
    cmd += ['-w', str(self.Timeout)]
    if self.DSCP and self.DSCP < 64:
      cmd += ['-Q', str(self.DSCP)]
    cmd += [self.Host]

    self.Result = ' '.join(cmd) + '\n'
    print '  %r' % cmd
    self.subproc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
    self.ioloop.add_handler(self.subproc.stdout.fileno(),
                            self._GotData, self.ioloop.READ)

  # pylint:disable=unused-argument
  def _GotData(self, fd, events):
    data = os.read(fd, 4096)
    if not data:
      self._EndProc()
    else:
      self.Result += data

  def _EndProc(self):
    print 'ping diagnostic finished.'
    if self.subproc:
      self.ioloop.remove_handler(self.subproc.stdout.fileno())
      if self.subproc.poll() is None:
        self.subproc.kill()
      self.subproc = None

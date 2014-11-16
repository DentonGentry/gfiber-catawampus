#!/usr/bin/python
# Copyright 2014 Google Inc. All Rights Reserved.
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
"""Device.IP.Diagnostics.X_CATAWAMPUS-ORG_HttpDownload.
"""

import os
import subprocess
import google3
import tornado.ioloop
import tr.mainloop
import tr.cwmptypes
import tr.x_catawampus_tr181_2_0


CATA181DEVICE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.Device
HTTPDOWNLOAD = CATA181DEVICE.X_CATAWAMPUS_ORG.HttpDownload
CURL = ['curl']


class DiagHttpDownload(HTTPDOWNLOAD):
  """Implementation of the HttpDownload vendor extension for TR-181."""
  IPVersion = tr.cwmptypes.Enum(
      ['Unspecified', 'IPv4', 'IPv6'], init='Unspecified')
  LimitMbps = tr.cwmptypes.Unsigned(0)
  Result = tr.cwmptypes.String('')
  Timeout = tr.cwmptypes.Unsigned(60)
  URL = tr.cwmptypes.String('')

  def __init__(self, ioloop=None):
    super(DiagHttpDownload, self).__init__()
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.subproc = None
    self.requested = False

  @LimitMbps.validator
  def LimitMbps(self, value):
    if value < 0:
      raise ValueError('ClientMbps must be >= 0')
    if value > 800:
      raise ValueError('ClientMbps must be < 800')
    return value

  @Timeout.validator
  def Timeout(self, value):
    if value <= 0:
      raise ValueError('Timeout  must be > 0')
    return value

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
    print 'http download starting.'
    if not self.URL:
      raise ValueError('HttpDownload.URL is not set')

    cmd = list(CURL)
    cmd += ['--max-time', str(self.Timeout)]
    cmd += ['--output', '/dev/null']
    cmd += ['--user-agent', 'Catawampus-Http-Diag']
    cmd += ['--verbose']

    if self.IPVersion == 'IPv4':
      cmd += ['--ipv4']
    elif self.IPVersion == 'IPv6':
      cmd += ['--ipv6']

    if self.LimitMbps:
      kbps = self.LimitMbps * 1000
      BytesPerSec = str(kbps / 8) + 'K'
      cmd += ['--limit-rate', BytesPerSec]

    cmd += [self.URL]

    self.Result = ' '.join(cmd) + '\n'
    print '  %r' % cmd
    self.subproc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
    self.ioloop.add_handler(self.subproc.stdout.fileno(),
                            self._GotData, self.ioloop.READ)

  # pylint:disable=unused-argument
  def _GotData(self, fd, events):
    data = os.read(fd, 4096)
    print 'GotData: ' + data
    if not data:
      self._EndProc()
    else:
      self.Result += data

  def _EndProc(self):
    print 'http download finished.'
    if self.subproc:
      self.ioloop.remove_handler(self.subproc.stdout.fileno())
      if self.subproc.poll() is None:
        self.subproc.kill()
      self.subproc = None

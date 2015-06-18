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
"""Device.IP.Diagnostics.X_CATAWAMPUS-ORG_Isostream.

Using the isostream program and run-isostream helper script.
"""

import datetime
import os
import signal
import subprocess
import time
import google3
import tornado.ioloop
import tr.cwmptypes
import tr.experiment
import tr.handle
import tr.mainloop
import tr.x_catawampus_tr181_2_0


CATA181DEVICE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.Device
ISOSTREAM = CATA181DEVICE.X_CATAWAMPUS_ORG.Isostream


@tr.experiment.Experiment
def IsostreamSerial(_):
  yield (ISOSTREAM + '.ServerEnable', True)
  yield (ISOSTREAM + '.ServerConcurrentConnections', 1)


@tr.experiment.Experiment
def IsostreamParallel(_):
  yield (ISOSTREAM + '.ServerEnable', True)
  yield (ISOSTREAM + '.ServerConcurrentConnections', 8)


@tr.experiment.Experiment
def Isostream5(_):
  yield (ISOSTREAM + '.ClientMbps', 5)


@tr.experiment.Experiment
def Isostream10(_):
  yield (ISOSTREAM + '.ClientMbps', 10)


@tr.experiment.Experiment
def Isostream14(_):
  yield (ISOSTREAM + '.ClientMbps', 14)


@tr.experiment.Experiment
def Isostream20(_):
  yield (ISOSTREAM + '.ClientMbps', 20)


def _KillWait(proc):
  proc.send_signal(signal.SIGTERM)
  for _ in xrange(30):
    if proc.poll() is not None:
      return
    time.sleep(0.1)
  print 'Warning: isostream failed to die after SIGTERM.'
  proc.kill()
  proc.wait()


class Isostream(ISOSTREAM):
  """Implementation of the Isostream vendor extension for TR-181."""
  ServerEnable = tr.cwmptypes.TriggerBool(False)
  ServerConcurrentConnections = tr.cwmptypes.Unsigned(0)
  ServerTimeLimit = tr.cwmptypes.Unsigned(60)
  ClientEnable = tr.cwmptypes.TriggerBool(False)
  ClientDisableIfPortActive = tr.cwmptypes.Unsigned(0)
  ClientTimeLimit = tr.cwmptypes.Unsigned(60)
  ClientRemoteIP = tr.cwmptypes.String('')
  ClientMbps = tr.cwmptypes.Unsigned(1)

  def __init__(self):
    super(Isostream, self).__init__()
    self.ioloop = tornado.ioloop.IOLoop.instance()
    self.serverproc = None
    self.servertimer = None
    self.clientproc = None
    self.clienttimer = None

  @ClientMbps.validator
  def ClientMbps(self, value):
    if value <= 0:
      raise ValueError('ClientMbps must be > 0')
    if value > 800:
      raise ValueError('ClientMbps must be < 800')
    return value

  @ServerTimeLimit.validator
  def ServerTimeLimit(self, value):
    if value <= 0:
      raise ValueError('ServerTimeLimit must be > 0')
    return value

  @ClientTimeLimit.validator
  def ClientTimeLimit(self, value):
    if value <= 0:
      raise ValueError('ClientTimeLimit must be > 0')
    return value

  @tr.mainloop.WaitUntilIdle
  def Triggered(self):
    server_changed = self.ServerEnable != (not not self.serverproc)
    client_changed = self.ClientEnable != (not not self.clientproc)

    if server_changed:
      if self.servertimer:
        self.ioloop.remove_timeout(self.servertimer)
        self.servertimer = None
      if self.serverproc:
        _KillWait(self.serverproc)
        self.serverproc = None
      if self.ServerEnable:
        argv = ['run-isostream-server']
        if self.ServerConcurrentConnections:
          argv += ['-P', self.ServerConcurrentConnections]
        self.serverproc = subprocess.Popen(argv, close_fds=True)
        if self.ServerTimeLimit:
          def _DisableServer():
            self.ServerEnable = False
          self.servertimer = self.ioloop.add_timeout(
              deadline=datetime.timedelta(seconds=self.ServerTimeLimit),
              callback=_DisableServer)

    if client_changed:
      if self.clienttimer:
        self.ioloop.remove_timeout(self.clienttimer)
        self.clienttimer = None
      if self.clientproc:
        _KillWait(self.clientproc)
        self.clientproc = None
      if self.ClientEnable:
        argv = ['run-isostream']
        env = dict(os.environ)  # make a copy
        env['ISOSTREAM_DISABLE_IF_PORT'] = str(self.ClientDisableIfPortActive)
        if self.ClientRemoteIP:
          argv += [self.ClientRemoteIP]
        else:
          argv += ['--use-storage-box']
        argv += ['-b', str(self.ClientMbps)]
        self.clientproc = subprocess.Popen(argv, env=env, close_fds=True)
        if self.ClientTimeLimit:
          def _DisableClient():
            self.ClientEnable = False
          self.clienttimer = self.ioloop.add_timeout(
              deadline=datetime.timedelta(seconds=self.ClientTimeLimit),
              callback=_DisableClient)


if __name__ == '__main__':
  isos = Isostream()
  print tr.handle.DumpSchema(isos)
  isos.ValidateExports()

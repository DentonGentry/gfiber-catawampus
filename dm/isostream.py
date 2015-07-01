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
import hmac
import logging
import os
import signal
import subprocess
import time
import google3
import tr.cwmptypes
import tr.experiment
import tr.filenotifier
import tr.handle
import tr.mainloop
import tr.x_catawampus_tr181_2_0


CATA181DEVICE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.Device
ISOSTREAM = CATA181DEVICE.X_CATAWAMPUS_ORG.Isostream
CONSENSUS_KEY_FILE = '/tmp/waveguide/consensus_key'


@tr.experiment.Experiment
def IsostreamSerial(_):
  return [(ISOSTREAM + '.ServerEnable', True),
          (ISOSTREAM + '.ServerConcurrentConnections', 1)]


@tr.experiment.Experiment
def IsostreamParallel(_):
  return [(ISOSTREAM + '.ServerEnable', True),
          (ISOSTREAM + '.ServerConcurrentConnections', 8)]


@tr.experiment.Experiment
def Isostream5(_):
  return [(ISOSTREAM + '.ClientMbps', 5)]


@tr.experiment.Experiment
def Isostream10(_):
  return [(ISOSTREAM + '.ClientMbps', 10)]


@tr.experiment.Experiment
def Isostream14(_):
  return [(ISOSTREAM + '.ClientMbps', 14)]


@tr.experiment.Experiment
def Isostream20(_):
  return [(ISOSTREAM + '.ClientMbps', 20)]


@tr.experiment.Experiment
def WhatIfWirelessTV(_):
  return [(ISOSTREAM + '.ClientEnable', True),
          (ISOSTREAM + '.ClientStartAtOrAfter', 1*60*60),
          (ISOSTREAM + '.ClientEndBefore', 6*60*60),
          (ISOSTREAM + '.ClientTimeLimit', 5*60)]


@tr.experiment.Experiment
def WhatIfWirelessTVSwarm(_):
  return [(ISOSTREAM + '.ClientEnable', True),
          (ISOSTREAM + '.ClientStartAtOrAfter', 1*60*60),
          (ISOSTREAM + '.ClientEndBefore', 1*60*60+1*60),
          (ISOSTREAM + '.ClientTimeLimit', 5*60)]


def _KillWait(proc):
  proc.send_signal(signal.SIGTERM)
  for _ in xrange(30):
    if proc.poll() is not None:
      return
    time.sleep(0.1)
  print 'Warning: isostream failed to die after SIGTERM.'
  proc.kill()
  proc.wait()


def _Unif(key):
  """Safely and uniformly produce a float in [0, 1) from a secret key.

  Args:
    key: a string of binary data, which may be a secret.

  Returns:
    a non-secret float sampled uniformly within [0, 1).
  """
  h = hmac.new(key, msg='42')
  return int(h.hexdigest(), base=16) / float(1 << 128)


class Isostream(ISOSTREAM):
  """Implementation of the Isostream vendor extension for TR-181."""
  ServerEnable = tr.cwmptypes.TriggerBool(False)
  ServerConcurrentConnections = tr.cwmptypes.Unsigned(0)
  ServerTimeLimit = tr.cwmptypes.Unsigned(60)
  ClientRunning = tr.cwmptypes.TriggerBool(False)
  ClientEnable = tr.cwmptypes.TriggerBool(False)
  ClientStartAtOrAfter = tr.cwmptypes.Unsigned(0)
  ClientEndBefore = tr.cwmptypes.Unsigned(86400)
  ClientDisableIfPortActive = tr.cwmptypes.Unsigned(0)
  ClientTimeLimit = tr.cwmptypes.Unsigned(60)
  ClientRemoteIP = tr.cwmptypes.String('')
  ClientMbps = tr.cwmptypes.Unsigned(1)

  def __init__(self):
    super(Isostream, self).__init__()
    mainloop = tr.mainloop.MainLoop()
    self.ioloop = mainloop.ioloop
    self.serverproc = None
    self.servertimer = None
    self.serversettings = None
    self.clientproc = None
    self.clienttimer = None
    self.clientsettings = None
    self.clientscheduletimer = None
    self.clientstarttime = None
    self.clientkey = None

    notifier = tr.filenotifier.FileNotifier(mainloop)
    self.watch = notifier.WatchObj(CONSENSUS_KEY_FILE, self._Rekey)
    self._Rekey()

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

  def _Rekey(self):
    try:
      with open(CONSENSUS_KEY_FILE) as f:
        clientkey = f.read()
        if self.clientkey != clientkey:
          self.clientkey = clientkey
    except IOError:
      logging.warning('Isostream: Could not read consensus key file "%s"',
                      CONSENSUS_KEY_FILE)
    self.Triggered()

  def _GetNextDeadline(self):
    """Figure out the next deadline for a scheduled isostream test.

    These deadlines are randomly picked within a [Start, End) interval
    specified by the data model.

    Returns:
      a POSIX timestamp, as from time.time(), when the test should next
      run; this is suitable to pass to IOLoop.add_timeout.
    """
    unif = _Unif(self.clientkey)
    self.clientstarttime = datetime.timedelta(
        seconds=(unif * (self.ClientEndBefore - self.ClientStartAtOrAfter) +
                 self.ClientStartAtOrAfter))

    lt = time.localtime()
    nowish, midnight = datetime.datetime(*lt[:6]), datetime.datetime(*lt[:3])
    deadline = midnight + self.clientstarttime - nowish
    if deadline < datetime.timedelta(seconds=1):
      deadline += datetime.timedelta(days=1)
    return deadline

  @tr.mainloop.WaitUntilIdle
  def Triggered(self):
    serversettings = (self.ServerConcurrentConnections, self.ServerTimeLimit)
    if (serversettings != self.serversettings or
        self.ServerEnable != (not not self.serverproc)):
      self.serversettings = serversettings
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

    clientsettings = (self.clientkey, self.ClientEnable,
                      self.ClientStartAtOrAfter, self.ClientEndBefore,
                      self.ClientDisableIfPortActive, self.ClientTimeLimit,
                      self.ClientRemoteIP, self.ClientMbps)
    if (clientsettings != self.clientsettings or
        self.ClientRunning != (not not self.clientproc)):
      self.clientsettings = clientsettings
      if self.clienttimer:
        self.ioloop.remove_timeout(self.clienttimer)
        self.clienttimer = None
      if self.clientproc:
        _KillWait(self.clientproc)
        self.clientproc = None
      if self.clientscheduletimer:
        self.ioloop.remove_timeout(self.clientscheduletimer)
        self.clientscheduletimer = None
      if self.ClientEnable:
        def _RunTest():
          self.ClientRunning = True
          self.clientscheduletimer = self.ioloop.add_timeout(
              deadline=self._GetNextDeadline(), callback=_RunTest)

        self.clientscheduletimer = self.ioloop.add_timeout(
            deadline=self._GetNextDeadline(), callback=_RunTest)
      if self.ClientRunning:
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
            self.ClientRunning = False
          self.clienttimer = self.ioloop.add_timeout(
              deadline=datetime.timedelta(seconds=self.ClientTimeLimit),
              callback=_DisableClient)


if __name__ == '__main__':
  isos = Isostream()
  print tr.handle.DumpSchema(isos)
  isos.ValidateExports()

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

import collections
import datetime
import errno
import hmac
import logging
import os
import re
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
ISOSTREAM_KEY = 'Device.X_CATAWAMPUS-ORG.Isostream.'

# Unit tests can override these.
BASEDIR = ['/tmp/waveguide']
CONSENSUS_KEY_FILE = ['/tmp/waveguide/consensus_key']


@tr.experiment.Experiment
def IsostreamSerial(_):
  if not subprocess.call(['is-storage-box']):
    return [(ISOSTREAM_KEY + 'ServerEnable', True),
            (ISOSTREAM_KEY + 'ServerConcurrentConnections', 1),
            (ISOSTREAM_KEY + 'ServerTimeLimit', 0)]


@tr.experiment.Experiment
def IsostreamParallel(_):
  if not subprocess.call(['is-storage-box']):
    return [(ISOSTREAM_KEY + 'ServerEnable', True),
            (ISOSTREAM_KEY + 'ServerConcurrentConnections', 8),
            (ISOSTREAM_KEY + 'ServerTimeLimit', 0)]


@tr.experiment.Experiment
def Isostream5(_):
  return [(ISOSTREAM_KEY + 'ClientMbps', 5)]


@tr.experiment.Experiment
def Isostream10(_):
  return [(ISOSTREAM_KEY + 'ClientMbps', 10)]


@tr.experiment.Experiment
def Isostream14(_):
  return [(ISOSTREAM_KEY + 'ClientMbps', 14)]


@tr.experiment.Experiment
def Isostream20(_):
  return [(ISOSTREAM_KEY + 'ClientMbps', 20)]


@tr.experiment.Experiment
def WhatIfTV(_):
  return [(ISOSTREAM_KEY + 'ClientRunOnSchedule', True),
          (ISOSTREAM_KEY + 'ClientStartAtOrAfter', 1*60*60),
          (ISOSTREAM_KEY + 'ClientEndBefore', 6*60*60),
          (ISOSTREAM_KEY + 'ClientTimeSufficient', 5*60),

          # The limit for all clients, when we're serializing requests, is:
          #
          #   $timeLimit = k * count(clients) * timeSufficient$
          #
          # where k is a 'fudge factor' based on conducting tests on unreliable
          # networks that allowed most six-node tests time enough to complete on
          # all nodes.

          (ISOSTREAM_KEY + 'ClientTimeLimit', 2*6*5*60)]


@tr.experiment.Experiment
def WhatIfTVPrimetime(_):
  return [(ISOSTREAM_KEY + 'ClientRunOnSchedule', True),
          (ISOSTREAM_KEY + 'ClientStartAtOrAfter', 19*60*60),
          (ISOSTREAM_KEY + 'ClientEndBefore', 22*60*60),
          (ISOSTREAM_KEY + 'ClientTimeSufficient', 5*60),

          # The limit for all clients, when we're serializing requests, is:
          #
          #   $timeLimit = k * count(clients) * timeSufficient$
          #
          # where k is a 'fudge factor' based on conducting tests on unreliable
          # networks that allowed most six-node tests time enough to complete on
          # all nodes.

          (ISOSTREAM_KEY + 'ClientTimeLimit', 2*6*5*60)]


@tr.experiment.Experiment
def WhatIfTVSwarm(_):
  return [(ISOSTREAM_KEY + 'ClientRunOnSchedule', True),
          (ISOSTREAM_KEY + 'ClientStartAtOrAfter', 1*60*60),
          (ISOSTREAM_KEY + 'ClientEndBefore', 1*60*60+1*60),
          (ISOSTREAM_KEY + 'ClientTimeLimit', 5*60)]


@tr.experiment.Experiment
def WhatIfTVPrimetimeSwarm(_):
  return [(ISOSTREAM_KEY + 'ClientRunOnSchedule', True),

          # The swarm experiments should be as stressful as possible, and complete as soon as
          # possible. My working hypothesis is 8PM is deeper into primetime, and thus has more load
          # on the network, than 7PM :).

          (ISOSTREAM_KEY + 'ClientStartAtOrAfter', 20*60*60),
          (ISOSTREAM_KEY + 'ClientEndBefore', 20*60*60+1*60),
          (ISOSTREAM_KEY + 'ClientTimeLimit', 5*60)]


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


LogLine = collections.namedtuple('LogLine', ['timestamp', 'offset',
                                             'disconn', 'drops'])


class Isostream(ISOSTREAM):
  """Implementation of the Isostream vendor extension for TR-181."""
  ServerEnable = tr.cwmptypes.TriggerBool(False)
  ServerConcurrentConnections = tr.cwmptypes.Unsigned(0)
  ServerTimeLimit = tr.cwmptypes.Unsigned(60)
  ClientEnable = tr.cwmptypes.TriggerBool(False)
  ClientEnableByScheduler = tr.cwmptypes.ReadOnlyBool(False)
  ClientRunOnSchedule = tr.cwmptypes.TriggerBool(False)
  ClientStartAtOrAfter = tr.cwmptypes.Unsigned(0)
  ClientEndBefore = tr.cwmptypes.Unsigned(86400)
  ClientDeadline = tr.cwmptypes.ReadOnlyDate()
  ClientDisableIfPortActive = tr.cwmptypes.Unsigned(0)
  ClientTimeSufficient = tr.cwmptypes.Unsigned(0)
  ClientTimeLimit = tr.cwmptypes.Unsigned(60)
  ClientRemoteIP = tr.cwmptypes.String('')
  ClientInterface = tr.cwmptypes.String('')
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
    self.clientkey = os.urandom(16)
    self.buffer = ''
    self.last_log = None

    try:
      os.makedirs(BASEDIR[0], 0755)
    except OSError as e:
      if e.errno != errno.EEXIST:
        raise

    notifier = tr.filenotifier.FileNotifier(mainloop)
    self.watch = notifier.WatchObj(CONSENSUS_KEY_FILE[0], self._Rekey)
    self._Rekey()

  def __del__(self):
    if self.serverproc:
      _KillWait(self.serverproc)
      self.serverproc = None
    if self.clientproc:
      self.ioloop.remove_handler(self.clientproc.stdout.fileno())
      _KillWait(self.clientproc)
      self.clientproc = None

  @ClientMbps.validator
  def ClientMbps(self, value):
    if value <= 0:
      raise ValueError('ClientMbps must be > 0')
    if value > 800:
      raise ValueError('ClientMbps must be < 800')
    return value

  @ServerTimeLimit.validator
  def ServerTimeLimit(self, value):
    if value < 0:
      raise ValueError('ServerTimeLimit must be >= 0')
    return value

  @ClientTimeLimit.validator
  def ClientTimeLimit(self, value):
    if value <= 0:
      raise ValueError('ClientTimeLimit must be > 0')
    return value

  def _Rekey(self):
    try:
      clientkey = open(CONSENSUS_KEY_FILE[0]).read()
    except IOError:
      logging.warning('Isostream: Could not read consensus key file "%s"',
                      CONSENSUS_KEY_FILE[0])
    else:
      if self.clientkey != clientkey:
        self.clientkey = clientkey
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

    Isostream.ClientDeadline.Set(self, time.time() + deadline.total_seconds())
    return deadline

  @property
  def ClientRunning(self):
    return not not self.clientproc

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
          argv += ['-P', str(self.ServerConcurrentConnections)]
        self.serverproc = subprocess.Popen(argv, close_fds=True)
        if self.ServerTimeLimit:
          def _DisableServer():
            self.ServerEnable = False
          self.servertimer = self.ioloop.add_timeout(
              deadline=datetime.timedelta(seconds=self.ServerTimeLimit),
              callback=_DisableServer)

    clientsettings = (self.clientkey, self.ClientEnable,
                      self.ClientRunOnSchedule, self.ClientStartAtOrAfter,
                      self.ClientEndBefore, self.ClientDisableIfPortActive,
                      self.ClientTimeLimit, self.ClientRemoteIP,
                      self.ClientMbps)

    clientshouldrun = (self.ClientEnable or self.ClientEnableByScheduler)

    if (clientsettings != self.clientsettings or
        clientshouldrun != self.ClientRunning):
      self.clientsettings = clientsettings
      if self.clienttimer:
        self.ioloop.remove_timeout(self.clienttimer)
        self.clienttimer = None
      if self.clientproc:
        self.ioloop.remove_handler(self.clientproc.stdout.fileno())
        _KillWait(self.clientproc)
        self.clientproc = None
      if self.clientscheduletimer:
        self.ioloop.remove_timeout(self.clientscheduletimer)
        self.clientscheduletimer = None

      if self.ClientRunOnSchedule:
        def _RunTest():
          Isostream.ClientEnableByScheduler.Set(self, True)
          self.clientscheduletimer = self.ioloop.add_timeout(
              deadline=self._GetNextDeadline(), callback=_RunTest)
          self.Triggered()

        self.clientscheduletimer = self.ioloop.add_timeout(
            deadline=self._GetNextDeadline(), callback=_RunTest)

      if clientshouldrun:
        argv = ['run-isostream']
        env = dict(os.environ)  # make a copy
        env['ISOSTREAM_DISABLE_IF_PORT'] = str(self.ClientDisableIfPortActive)
        if self.ClientRemoteIP:
          argv += [self.ClientRemoteIP]
        else:
          argv += ['--use-storage-box']

        if self.ClientInterface:
          argv += ['-I', self.ClientInterface]

        if self.ClientTimeSufficient:
          argv += ['-s', str(self.ClientTimeSufficient)]

        argv += ['-b', str(self.ClientMbps)]
        self.clientproc = subprocess.Popen(argv, env=env,
                                           stdout=subprocess.PIPE,
                                           close_fds=True)
        self.ioloop.add_handler(self.clientproc.stdout.fileno(), self.GetLines,
                                self.ioloop.READ)
        if self.ClientTimeLimit:
          def _DisableClient():
            Isostream.ClientEnableByScheduler.Set(self, False)
            self.Triggered()

          self.clienttimer = self.ioloop.add_timeout(
              deadline=datetime.timedelta(seconds=self.ClientTimeLimit),
              callback=_DisableClient)

  def GetLines(self, fd, events):
    data = os.read(fd, 4096)
    self.buffer += data
    while '\n' in self.buffer:
      before, after = self.buffer.split('\n', 1)
      self.buffer = after
      self.ParseLineToTuple(before)

  def ParseLineToTuple(self, line):
    line = line.strip()
    values = re.match(
        (r'(%(real)s).*offset=(%(real)s).*disconn=(\d*).*drops=(\d*)' %
         {'real': r'-?\d*\.?\d*'}),
        line)
    if values:
      timestamp, offset, disconn, drops = values.groups()
      self.last_log = LogLine(float(timestamp), float(offset),
                              int(disconn), int(drops))

if __name__ == '__main__':
  isos = Isostream()
  print tr.handle.DumpSchema(isos)
  isos.ValidateExports()

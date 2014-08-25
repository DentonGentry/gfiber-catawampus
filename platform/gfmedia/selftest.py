#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
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

"""Implementation of the X_GOOGLE_COM_SELFTEST model."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import calendar
import datetime
import os
import select
import signal
import subprocess

import google3
import tornado.ioloop
import tr.core
import tr.mainloop
import tr.cwmptypes
import tr.x_selftest_1_0


BASE = tr.x_selftest_1_0.X_GOOGLE_COM_SELFTEST_v1_0

# this can be redefined in unit tests
STRESSTEST_BIN = 'stresstest 2>&1 | tee /proc/self/fd/2 | logos stresstest'
IPERF_BIN = 'iperf 2>&1 | tee /proc/self/fd/2 | logos iperf'
TIMENOW = datetime.datetime.now


class SelfTest(BASE.X_GOOGLE_COM_GFIBERTV.SelfTest):
  """Controls for a self-test module."""

  def __init__(self, loop=None):
    super(SelfTest, self).__init__()
    self.loop = loop or tornado.ioloop.IOLoop.instance()
    self.ServerIP = None
    self.AutoRestartEnable = False
    self.MaxBitRate = -1
    self.Mode = 'None'
    self.LastResult = 0
    self.Log = ''
    self.proc = None

  Mode = tr.cwmptypes.TriggerEnum(['None', 'Success', 'Error',
                               'StressTest', 'Throughput'])
  ServerIP = tr.cwmptypes.TriggerString()
  AutoRestartEnable = tr.cwmptypes.TriggerBool()
  MaxBitRate = tr.cwmptypes.TriggerFloat()
  LastResultTime = tr.cwmptypes.ReadOnlyDate()

  def _StressTest(self):
    print 'starting selftest process.'
    self.Log = ''
    env = dict(os.environ)
    env.pop('SERVER_IP', 0)
    env.pop('DONT_ABORT', 0)
    env.pop('MAX_BANDWIDTH', 0)
    if self.ServerIP:
      env['SERVER_IP'] = str(self.ServerIP)
    if self.AutoRestartEnable:
      env['DONT_ABORT'] = '1'
    if self.MaxBitRate >= 0:
      env['MAX_BANDWIDTH'] = '%d' % self.MaxBitRate  # megabits/sec
    return (STRESSTEST_BIN, env)

  def _Throughput(self):
    print 'starting iperf.'
    self.Log = ''
    env = dict(os.environ)
    env.pop('IPERF_CLIENT', 0)
    env.pop('IPERF_SERVER', 0)
    env.pop('IPERF_TIME', 0)
    env.pop('TCP_WINDOW_SIZE', 0)
    if self.ServerIP:
      env['IPERF_CLIENT'] = str(self.ServerIP)
      env['IPERF_TIME'] = '40'
    else:
      env['IPERF_SERVER'] = '1'
    env['TCP_WINDOW_SIZE'] = '1M'
    return (IPERF_BIN, env)

  def _StartTest(self, exe, env):
    def preexec():
      # give child process its own process group to make it easier to kill
      os.setpgid(0, 0)
    self.proc = subprocess.Popen(exe, shell=True, env=env,
                                 preexec_fn=preexec,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
    self.loop.add_handler(self.proc.stdout.fileno(),
                          lambda fd, events: self._ReadData(timeout=0),
                          tornado.ioloop.IOLoop.READ)
    self.loop.add_handler(self.proc.stderr.fileno(),
                          lambda fd, events: self._ReadData(timeout=0),
                          tornado.ioloop.IOLoop.READ)

  @tr.mainloop.WaitUntilIdle
  def Triggered(self):
    """After values have been changed, finalize the results here."""
    if self.proc:
      print 'killing selftest process.'
      assert self.proc.pid > 0
      os.kill(-self.proc.pid, signal.SIGTERM)  # kill whole process group
      for _ in range(5):
        self._ReadData(timeout=1.0)
        if not self.proc:
          break
      if self.proc:
        self.proc.kill()
      self._Finish()
    if self.Mode == 'StressTest':
      (exe, env) = self._StressTest()
      self._StartTest(exe, env)
    if self.Mode == 'Throughput':
      (exe, env) = self._Throughput()
      self._StartTest(exe, env)

  def _Finish(self):
    self.Mode = 'None'
    if self.proc:
      self.LastResult = self.proc.wait()
      type(self).LastResultTime.Set(
          self, calendar.timegm(TIMENOW().timetuple()))
      self.proc = None

  def _ReadData(self, timeout):
    socks = [self.proc.stdout, self.proc.stderr]
    while socks:
      r, _, _ = select.select(socks, [], [], timeout)
      if not r:
        # no more data, but not EOF
        return
      for sock in r:
        buf = os.read(sock.fileno(), 4096)
        if not buf:
          socks.remove(sock)
          loop = tornado.ioloop.IOLoop.instance()
          loop.remove_handler(sock.fileno())
        self.Log += buf
      self.Log = self.Log[-100000:]  # limit maximum log size

    # if we get here, socks is empty: EOF on both sockets
    self._Finish()


if __name__ == '__main__':
  print tr.core.DumpSchema(SelfTest)

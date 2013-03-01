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

import os
import select
import signal
import subprocess

import google3
import tornado.ioloop
import tr.core
import tr.mainloop
import tr.types
import tr.x_selftest_1_0


BASE = tr.x_selftest_1_0.X_GOOGLE_COM_SELFTEST_v1_0

# this can be redefined in unit tests
STRESSTEST_BIN = 'stresstest 2>&1 | tee /proc/self/fd/2 | logos stresstest'


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

  Mode = tr.types.TriggerEnum(['None', 'Success', 'Error', 'StressTest'])
  ServerIP = tr.types.TriggerString()
  AutoRestartEnable = tr.types.TriggerBool()
  MaxBitRate = tr.types.TriggerFloat()

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
      print 'starting selftest process.'
      self.Log = ''
      env = dict(os.environ)
      if self.ServerIP:
        env['SERVER_IP'] = str(self.ServerIP)
      if self.AutoRestartEnable:
        env['DONT_ABORT'] = '1'
      if self.MaxBitRate >= 0:
        env['MAX_BANDWIDTH'] = '%d' % self.MaxBitRate  # megabits/sec

      def preexec():
        # give child process its own process group to make it easier to kill
        os.setpgid(0, 0)
      self.proc = subprocess.Popen(STRESSTEST_BIN, shell=True, env=env,
                                   preexec_fn=preexec,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
      self.loop.add_handler(self.proc.stdout.fileno(),
                            lambda fd, events: self._ReadData(timeout=0),
                            tornado.ioloop.IOLoop.READ)
      self.loop.add_handler(self.proc.stderr.fileno(),
                            lambda fd, events: self._ReadData(timeout=0),
                            tornado.ioloop.IOLoop.READ)

  def _Finish(self):
    self.Mode = 'None'
    if self.proc:
      self.LastResult = self.proc.wait()
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

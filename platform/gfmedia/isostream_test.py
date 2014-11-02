#!/usr/bin/python
# Copyright 2013 Google Inc. All Rights Reserved.
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

# unittest requires method names starting in 'test'
# pylint:disable=invalid-name

"""Unit tests for Isostream implementation."""

import os
import time
import google3
import isostream
from tr.wvtest import unittest
import tr.helpers
import tr.mainloop


class IsostreamTest(unittest.TestCase):
  """Tests for isostream.py."""

  def setUp(self):
    self.readyfile = 'isos.out.%d.ready' % os.getpid()
    self.logfile = 'isos.out.%d.tmp' % os.getpid()
    tr.helpers.Unlink(self.logfile)
    tr.helpers.Unlink(self.readyfile)
    self.oldpath = os.environ['PATH']
    os.environ['PATH'] = '%s/testdata/isostream:%s' % (os.getcwd(),
                                                       os.environ['PATH'])
    self.loop = tr.mainloop.MainLoop()

  def tearDown(self):
    os.environ['PATH'] = self.oldpath
    tr.helpers.Unlink(self.logfile)
    tr.helpers.Unlink(self.readyfile)

  def _WaitReady(self):
    for i in range(1000):
      if os.path.exists(self.readyfile):
        return
      time.sleep(0.01)
    raise Exception('readyfile %r not created after a long time'
                    % self.readyfile)

  def _Iter(self, expect):
    tr.helpers.Unlink(self.readyfile)
    self.loop.RunOnce()
    self._WaitReady()
    self.assertEqual(open(self.logfile).read(), expect)
    tr.helpers.Unlink(self.logfile)

  def testServer(self):
    isos = isostream.Isostream()
    isos.ServerEnable = True
    self._Iter('run-isostream-server\n')
    isos.ServerEnable = False
    self._Iter('DEAD run-isostream-server\n')
    isos.ServerTimeLimit = 1
    self.assertRaises(ValueError, lambda: setattr(isos, 'ServerTimeLimit', 0))
    isos.ServerEnable = True
    self._Iter('run-isostream-server\n')
    time.sleep(1)
    self._Iter('DEAD run-isostream-server\n')

  def testClient(self):
    isos = isostream.Isostream()
    isos.ClientEnable = True
    self._Iter('run-isostream --use-storage-box -b 1\n')
    isos.ClientEnable = False
    self._Iter('DEAD run-isostream\n')
    isos.ClientTimeLimit = 1
    self.assertRaises(ValueError, lambda: setattr(isos, 'ClientTimeLimit', 0))
    isos.ClientMbps = 99
    isos.ClientRemoteIP = '1.2.3.4'
    isos.ClientEnable = True
    self._Iter('run-isostream 1.2.3.4 -b 99\n')
    # Validate that we can run client and server at the same time
    isos.ServerEnable = True
    self._Iter('run-isostream-server\n')
    time.sleep(1)
    self._Iter('DEAD run-isostream\n')
    isos.ServerEnable = False
    self._Iter('DEAD run-isostream-server\n')

if __name__ == '__main__':
  unittest.main()

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

# unittest requires method names starting in 'test'
# pylint:disable=invalid-name

"""Unit tests for selftest.py."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import datetime
import signal
import google3
import selftest
import tr.handle
import tr.mainloop
from tr.wvtest import unittest


class TimeNow(object):

  def timetuple(self):
    return (2013, 1, 2, 3, 4, 5)


class SelfTestTest(unittest.TestCase):

  def setUp(self):
    selftest.TIMENOW = TimeNow

  def testSelfTest(self):
    st = selftest.SelfTest()
    loop = tr.mainloop.MainLoop()
    tr.handle.ValidateExports(st)

    selftest.STRESSTEST_BIN = 'echo hi $DONT_ABORT $SERVER_IP $MAX_BANDWIDTH'
    self.assertEqual(st.Log, '')
    self.assertEqual(st.LastResult, 0)
    st.Mode = 'StressTest'
    while st.Mode == 'StressTest':
      loop.RunOnce()
    self.assertEqual(st.Log, 'hi\n')
    self.assertEqual(st.Mode, 'None')
    self.assertEqual(st.LastResult, 0)

    selftest.STRESSTEST_BIN = (
        'echo hi2 $DONT_ABORT $SERVER_IP $MAX_BANDWIDTH\n'
        'exit 24'
    )
    st.ServerIP = '1.2.3.4'
    st.AutoRestartEnable = True
    st.MaxBitRate = 12.345678
    st.Mode = 'StressTest'
    while st.Mode == 'StressTest':
      loop.RunOnce()
    self.assertEqual(st.Log, 'hi2 1 1.2.3.4 12\n')
    self.assertEqual(st.Mode, 'None')
    self.assertEqual(st.LastResult, 24)
    self.assertEqual(st.LastResultTime,
                     datetime.datetime(2013, 1, 2, 3, 4, 5))

    selftest.STRESSTEST_BIN = 'sleep 1000'
    st.Mode = 'StressTest'
    for _ in range(10):
      loop.RunOnce(0)
    self.assertEqual(st.Log, '')
    self.assertEqual(st.Mode, 'StressTest')
    self.assertEqual(st.LastResult, 24)
    st.Mode = 'None'
    loop.RunOnce()
    self.assertEqual(st.LastResult, -signal.SIGTERM)

  def testIPerf(self):
    st = selftest.SelfTest()
    loop = tr.mainloop.MainLoop()
    tr.handle.ValidateExports(st)
    selftest.IPERF_BIN = 'echo hi $IPERF_CLIENT $IPERF_SERVER $IPERF_TIME'

    self.assertEqual(st.Log, '')
    self.assertEqual(st.LastResult, 0)
    st.Mode = 'Throughput'
    while st.Mode == 'Throughput':
      loop.RunOnce()
    self.assertEqual(st.Log, 'hi 1\n')
    self.assertEqual(st.Mode, 'None')
    self.assertEqual(st.LastResult, 0)
    self.assertEqual(st.LastResultTime,
                     datetime.datetime(2013, 1, 2, 3, 4, 5))

    st.ServerIP = '1.1.1.1'
    st.Mode = 'Throughput'
    while st.Mode == 'Throughput':
      loop.RunOnce()
    self.assertEqual(st.Log, 'hi 1.1.1.1 40\n')
    self.assertEqual(st.Mode, 'None')
    self.assertEqual(st.LastResult, 0)


if __name__ == '__main__':
  unittest.main()

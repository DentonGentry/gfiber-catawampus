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
# pylint: disable-msg=C6409

"""Unit tests for selftest.py."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import signal
import unittest

import google3
import tr.mainloop
import selftest


class SelfTestTest(unittest.TestCase):
  def testSelfTest(self):
    st = selftest.SelfTest()
    loop = tr.mainloop.MainLoop()
    st.ValidateExports()

    selftest.STRESSTEST_BIN = 'echo hi $DONT_ABORT $SERVER_IP $MAX_BANDWIDTH'
    self.assertEquals(st.Log, '')
    self.assertEquals(st.LastResult, 0)
    st.Mode = 'StressTest'
    while st.Mode == 'StressTest':
      loop.RunOnce()
    self.assertEqual(st.Log, 'hi\n')
    self.assertEquals(st.Mode, 'None')
    self.assertEquals(st.LastResult, 0)

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
    self.assertEquals(st.Mode, 'None')
    self.assertEquals(st.LastResult, 24)

    selftest.STRESSTEST_BIN = 'sleep 1000'
    st.Mode = 'StressTest'
    for _ in range(10):
      loop.RunOnce(0)
    self.assertEqual(st.Log, '')
    self.assertEquals(st.Mode, 'StressTest')
    self.assertEquals(st.LastResult, 24)
    st.Mode = 'None'
    loop.RunOnce()
    self.assertEquals(st.LastResult, -signal.SIGTERM)


if __name__ == '__main__':
  unittest.main()

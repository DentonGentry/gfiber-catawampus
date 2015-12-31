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

"""Unit tests for speedtest datamodel implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import datetime
import os
import shutil
import google3
import speedtest
import tr.handle
import tr.mainloop
from tr.wvtest import unittest


class TimeNow(object):

  def timetuple(self):
    return (2013, 1, 2, 3, 4, 5)


class OoklaTest(unittest.TestCase):
  """Tests for speedtest.py."""

  def setUp(self):
    self.loop = tr.mainloop.MainLoop()
    speedtest.FIBERSPEEDTEST = '/nosuchbinary'
    speedtest.OOKLACLIENT = '/nosuchbinary'
    speedtest.OOKLACLIENTDIR = '/tmp/speedtest_test.%d' % os.getpid()
    speedtest.TIMENOW = TimeNow

  def tearDown(self):
    shutil.rmtree(speedtest.OOKLACLIENTDIR, ignore_errors=True)

  def _SetOoklaClient(self):
    c = 'testdata/speedtest/OoklaClient'
    speedtest.OOKLACLIENT = os.path.join(os.getcwd(), c)

  def _SetFiberSpeedtest(self):
    c = 'testdata/speedtest/fiberspeedtest'
    speedtest.FIBERSPEEDTEST = os.path.join(os.getcwd(), c)

  def _DoSpeedtest(self, stst):
    stst.DiagnosticsState = 'Requested'
    while stst.DiagnosticsState == 'Requested':
      self.loop.RunOnce(timeout=5)

  def testValidateExports(self):
    stst = speedtest.Speedtest(self.loop.ioloop)
    tr.handle.ValidateExports(stst)

  def testOoklaSpeedtest(self):
    self._SetOoklaClient()
    stst = speedtest.Speedtest(self.loop.ioloop)
    licenseexpected = 'This is a license'
    stst.License = licenseexpected
    stst.Arguments = '--right'
    self._DoSpeedtest(stst)
    licensepath = os.path.join(speedtest.OOKLACLIENTDIR, 'settings.xml')
    licenseactual = open(licensepath).read()
    self.assertEqual(licenseexpected, licenseactual)
    self.assertEqual(stst.Output, 'Ookla speedtest output\n')
    self.assertEqual(stst.DiagnosticsState, 'Complete')
    self.assertEqual(stst.LastResultTime,
                     datetime.datetime(2013, 1, 2, 3, 4, 5))

  def testOoklaSpeedtestFails(self):
    self._SetOoklaClient()
    stst = speedtest.Speedtest(self.loop.ioloop)
    stst.Arguments = '--wrong'
    self._DoSpeedtest(stst)
    self.assertEqual(stst.DiagnosticsState, 'Error_Internal')

  def testFiberSpeedtest(self):
    self._SetFiberSpeedtest()
    stst = speedtest.Speedtest(self.loop.ioloop)
    stst.Arguments = '--right'
    self._DoSpeedtest(stst)
    self.assertEqual(stst.Output, 'Fiber speedtest output\n')
    self.assertEqual(stst.DiagnosticsState, 'Complete')
    self.assertEqual(stst.LastResultTime,
                     datetime.datetime(2013, 1, 2, 3, 4, 5))

  def testFiberSpeedtestFails(self):
    self._SetFiberSpeedtest()
    stst = speedtest.Speedtest(self.loop.ioloop)
    stst.Arguments = '--wrong'
    self._DoSpeedtest(stst)
    self.assertEqual(stst.DiagnosticsState, 'Error_Internal')

  def testBothSpeedtestMissing(self):
    speedtest.FIBERSPEEDTEST = '/nosuchbinary'
    speedtest.OOKLACLIENT = '/nosuchbinary'
    stst = speedtest.Speedtest(self.loop.ioloop)
    stst.Arguments = '--right'
    self._DoSpeedtest(stst)
    self.assertEqual(stst.DiagnosticsState, 'Error_Internal')


if __name__ == '__main__':
  unittest.main()

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
# pylint: disable-msg=C6409

"""Unit tests for Ookla speedtest implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import datetime
import os
import shutil
import google3
from tr.wvtest import unittest
import tr.mainloop
import ookla


class TimeNow(object):
  def timetuple(self):
    return (2013, 1, 2, 3, 4, 5)


class OoklaTest(unittest.TestCase):
  """Tests for ookla.py."""

  def setUp(self):
    self.loop = tr.mainloop.MainLoop()
    ookla.SPEEDTEST = os.path.join(os.getcwd(), 'testdata/ookla/OoklaClient')
    ookla.SPEEDTESTDIR = '/tmp/ookla_test.%d' % os.getpid()
    ookla.TIMENOW = TimeNow

  def tearDown(self):
    shutil.rmtree(ookla.SPEEDTESTDIR, ignore_errors=True)

  def _DoSpeedtest(self, ooklatest):
    ooklatest.DiagnosticsState = 'Requested'
    while ooklatest.DiagnosticsState == 'Requested':
      self.loop.RunOnce(timeout=5)

  def testValidateExports(self):
    ooklatest = ookla.Speedtest(self.loop.ioloop)
    ooklatest.ValidateExports()

  def testSpeedtest(self):
    ooklatest = ookla.Speedtest(self.loop.ioloop)
    licenseexpected = 'This is a license'
    ooklatest.License = licenseexpected
    ooklatest.Arguments = '--right'
    self._DoSpeedtest(ooklatest)
    licensepath = os.path.join(ookla.SPEEDTESTDIR, 'settings.xml')
    licenseactual = open(licensepath).read()
    self.assertEqual(licenseexpected, licenseactual)
    self.assertEqual(ooklatest.Output, 'Speedtest output\n')
    self.assertEqual(ooklatest.DiagnosticsState, 'Complete')
    self.assertEqual(ooklatest.LastResultTime,
                     datetime.datetime(2013, 1, 2, 3, 4, 5))

  def testSpeedtestFails(self):
    ooklatest = ookla.Speedtest(self.loop.ioloop)
    ooklatest.Arguments = '--wrong'
    self._DoSpeedtest(ooklatest)
    self.assertEqual(ooklatest.DiagnosticsState, 'Error_Internal')

  def testSpeedtestMissing(self):
    ookla.SPEEDTEST = '/nosuchbinary'
    ooklatest = ookla.Speedtest(self.loop.ioloop)
    ooklatest.Arguments = '--irrelevant'
    self._DoSpeedtest(ooklatest)
    self.assertEqual(ooklatest.DiagnosticsState, 'Error_Internal')


if __name__ == '__main__':
  unittest.main()

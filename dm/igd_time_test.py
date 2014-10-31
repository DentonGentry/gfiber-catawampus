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

"""Unit tests for igd_time.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import tempfile
import google3
from tr.wvtest import unittest
import igd_time
import tr.handle
import tr.mainloop


def TimeNow():
  return 1234567890.987654


class IgdTimeTest(unittest.TestCase):
  SAVEDATTRIBUTES = ['TIMENOW', 'LOCALTIMEFILE', 'TIMESYNCEDFILE',
                     'TZFILE']

  def saveAttributes(self):
    self.saved_attributes = {}
    for attr in self.SAVEDATTRIBUTES:
      self.saved_attributes[attr] = getattr(igd_time, attr)

  def restoreAttributes(self):
    for (attr, val) in self.saved_attributes.iteritems():
      setattr(igd_time, attr, val)

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()
    self.loop = tr.mainloop.MainLoop()
    self.saveAttributes()
    self.localtimefile = os.path.join(self.tmpdir, 'localtime')
    igd_time.LOCALTIMEFILE = self.localtimefile
    igd_time.TIMENOW = TimeNow
    self.tzfile = os.path.join(self.tmpdir, 'tz')
    igd_time.TZFILE = self.tzfile

  def tearDown(self):
    self.restoreAttributes()
    shutil.rmtree(self.tmpdir)

  def testValidateExports(self):
    t = igd_time.TimeTZ()
    tr.handle.ValidateExports(t)

  def testCurrentLocalTime(self):
    t = igd_time.TimeTZ()
    self.assertEqual(t.CurrentLocalTime, '2009-02-13T23:31:30.987654Z')

  def testGetLocalTimeZoneName(self):
    igd_time.TZFILE = 'testdata/igd_time/TZ'
    t = igd_time.TimeTZ()
    self.assertEqual(t.LocalTimeZoneName, 'POSIX')

  def testSetLocalTimeZoneName(self):
    t = igd_time.TimeTZ()
    t.LocalTimeZoneName = 'UTC0'
    self.loop.RunOnce(timeout=1)
    expectedTZ = 'UTC0\n'
    actualTZ = open(self.tzfile).read()
    self.assertEqual(actualTZ, expectedTZ)
    # UTCtzfile copied from /usr/share/zoneinfo/posix/UTC,
    # and modified with hex editor to remove the portions
    # not handled by igd_time.py
    expectedLT = open('testdata/igd_time/UTCtzfile').read()
    actualLT = open(self.localtimefile).read()
    self.assertEqual(actualLT, expectedLT)

  def testUCLibcIsReallyReallyReallyPickyAboutWhitespace(self):
    # uClibC will only accept a TZ file with exactly one newline at the end.
    tzwrite = 'PST8PDT,M3.2.0/2,M11.1.0/2'

    t = igd_time.TimeTZ()
    t.LocalTimeZoneName = tzwrite + '\n\n\n\n\n'
    self.loop.RunOnce(timeout=1)
    actual = open(self.tzfile).read()
    self.assertEqual(actual, tzwrite + '\n')

    os.remove(self.tzfile)
    t = igd_time.TimeTZ()
    t.LocalTimeZoneName = tzwrite
    self.loop.RunOnce(timeout=1)
    actual = open(self.tzfile).read()
    self.assertEqual(actual, tzwrite + '\n')

  def testIncorrectPosixTzNotThatAcsWouldEverSendOneNopeNopeNope(self):
    t = igd_time.TimeTZ()
    t.LocalTimeZoneName = 'This is not a timezone'
    self.loop.RunOnce(timeout=1)
    self.assertFalse(os.path.exists(self.localtimefile))
    self.assertFalse(os.path.exists(self.tzfile))

  def testTimeSyncedStatus(self):
    t = igd_time.TimeTZ()
    igd_time.TIMESYNCEDFILE = '/nonexistant'
    self.assertEqual(t.Status, 'Unsynchronized')
    igd_time.TIMESYNCEDFILE = 'testdata/igd_time/time.synced'
    self.assertEqual(t.Status, 'Synchronized')


if __name__ == '__main__':
  unittest.main()

#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for igd_time.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import tempfile
import unittest

import google3
import igd_time


def TimeNow():
  return 1234567890.987654


class IgdTimeTest(unittest.TestCase):
  def setUp(self):
    self.old_TIMENOW = igd_time.TIMENOW
    igd_time.TIMENOW = TimeNow
    self.files_to_remove = list()

  def tearDown(self):
    igd_time.TIMENOW = self.old_TIMENOW
    for f in self.files_to_remove:
      os.remove(f)

  def MakeTestScript(self):
    """Create a unique file in /tmp."""
    outfile = tempfile.NamedTemporaryFile(delete=False)
    self.files_to_remove.append(outfile.name)
    return outfile

  def testValidateExports(self):
    t = igd_time.TimeTZ()
    t.ValidateExports()

  def testCurrentLocalTime(self):
    t = igd_time.TimeTZ()
    self.assertEqual(t.CurrentLocalTime, '2009-02-13T23:31:30.987654Z')

  def testGetLocalTimeZoneName(self):
    t = igd_time.TimeTZ(tzfile='testdata/igd_time/TZ')
    self.assertEqual(t.LocalTimeZoneName, 'POSIX')

  def testSetLocalTimeZoneName(self):
    outfile = self.MakeTestScript()
    t = igd_time.TimeTZ(tzfile=outfile.name)
    expected = 'PST8PDT,M3.2.0/2,M11.1.0/2'
    t.StartTransaction()
    t.LocalTimeZoneName = expected
    t.CommitTransaction()
    self.assertEqual(outfile.read().strip(), expected)

  def testUCLibcIsReallyReallyReallyPickyAboutWhitespace(self):
    # uClibC will only accept a TZ file with exactly one newline at the end.
    tzwrite = 'PST8PDT,M3.2.0/2,M11.1.0/2'

    outfile = self.MakeTestScript()
    t = igd_time.TimeTZ(tzfile=outfile.name)
    t.StartTransaction()
    t.LocalTimeZoneName = tzwrite + '\n\n\n\n\n'
    t.CommitTransaction()
    self.assertEqual(outfile.read(), tzwrite + '\n')

    outfile = self.MakeTestScript()
    t = igd_time.TimeTZ(tzfile=outfile.name)
    t.StartTransaction()
    t.LocalTimeZoneName = tzwrite
    t.CommitTransaction()
    self.assertEqual(outfile.read(), tzwrite + '\n')

  def testAbandonTransaction(self):
    outfile = self.MakeTestScript()
    t = igd_time.TimeTZ(tzfile=outfile.name)
    t.StartTransaction()
    t.LocalTimeZoneName = 'This should not be written.'
    t.AbandonTransaction()
    self.assertEqual(outfile.read().strip(), '')


if __name__ == '__main__':
  unittest.main()

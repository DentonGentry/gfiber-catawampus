#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for cwmpdate.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import calendar
import datetime
import unittest

import google3
import cwmpdate


class UTC(datetime.tzinfo):
  def utcoffset(self, dt):
    return datetime.timedelta(0)

  def tzname(self, dt):
    return 'UTC'

  def dst(self, dt):
    return datetime.timedelta(0)


class OTH(datetime.tzinfo):
  def utcoffset(self, dt):
    return datetime.timedelta(0, 3600)

  def tzname(self, dt):
    return 'OTH'

  def dst(self, dt):
    return datetime.timedelta(0, 3600)


class CwmpDateTest(unittest.TestCase):
  """Tests for date formatting."""

  def testDatetimeNone(self):
    self.assertEqual('0001-01-01T00:00:00Z', cwmpdate.format(None))

  def testDatetimeNaive(self):
    dt = datetime.datetime(1999, 12, 31, 23, 59, 58, 999999)
    self.assertEqual('1999-12-31T23:59:58.999999Z', cwmpdate.format(dt))
    dt2 = datetime.datetime(1999, 12, 31, 23, 59, 58)
    self.assertEqual('1999-12-31T23:59:58Z', cwmpdate.format(dt2))

  def testDatetimeUTC(self):
    dt = datetime.datetime(1999, 12, 31, 23, 59, 58, 999999, tzinfo=UTC())
    self.assertEqual('1999-12-31T23:59:58.999999Z', cwmpdate.format(dt))
    dt2 = datetime.datetime(1999, 12, 31, 23, 59, 58, tzinfo=UTC())
    self.assertEqual('1999-12-31T23:59:58Z', cwmpdate.format(dt2))

  def testDatetimeOTH(self):
    dt = datetime.datetime(1999, 12, 31, 23, 59, 58, 999999, tzinfo=OTH())
    self.assertEqual('1999-12-31T23:59:58.999999+01:00',
                     cwmpdate.format(dt))

  def testTimedelta(self):
    t = 1234567890.987654
    self.assertEqual('2009-02-13T23:31:30.987654Z', cwmpdate.format(t))

  def testParse(self):
    dt = cwmpdate.parse('2012-01-12T00:20:03.217691Z')
    timestamp = calendar.timegm(dt.timetuple())
    self.assertEqual(timestamp, 1326327603.0)

  def testValid(self):
    self.assertTrue(cwmpdate.valid('2009-02-13T23:31:30.987654Z'))
    self.assertTrue(cwmpdate.valid('2009-02-13T23:31:30Z'))
    self.assertFalse(cwmpdate.valid('2009-02-13T23:31:30'))
    self.assertFalse(cwmpdate.valid('booga'))


if __name__ == '__main__':
  unittest.main()

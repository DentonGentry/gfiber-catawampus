#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for cwmpdate.py"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import cwmpdate
import datetime
import unittest

class UTC(datetime.tzinfo):
  def utcoffset(self, dt):
    return datetime.timedelta(0)
  def tzname(self, dt):
    return "UTC"
  def dst(self, dt):
    return datetime.timedelta(0)

class OTH(datetime.tzinfo):
  def utcoffset(self, dt):
    return datetime.timedelta(0, 3600)
  def tzname(self, dt):
    return "OTH"
  def dst(self, dt):
    return datetime.timedelta(0, 3600)

class CwmpDateTest(unittest.TestCase):
  """Tests for date formatting."""

  def testDatetimeNone(self):
    self.assertEqual("0001-01-01T00:00:00Z", cwmpdate.cwmpformat(None))

  def testDatetimeNaive(self):
    dt = datetime.datetime(1999, 12, 31, 23, 59, 58, 999999)
    self.assertEqual("1999-12-31T23:59:58.999999Z", cwmpdate.cwmpformat(dt))
    dt2 = datetime.datetime(1999, 12, 31, 23, 59, 58)
    self.assertEqual("1999-12-31T23:59:58Z", cwmpdate.cwmpformat(dt2))


  def testDatetimeUTC(self):
    dt = datetime.datetime(1999, 12, 31, 23, 59, 58, 999999, tzinfo=UTC())
    self.assertEqual("1999-12-31T23:59:58.999999Z", cwmpdate.cwmpformat(dt))
    dt2 = datetime.datetime(1999, 12, 31, 23, 59, 58, tzinfo=UTC())
    self.assertEqual("1999-12-31T23:59:58Z", cwmpdate.cwmpformat(dt2))

  def testDatetimeOTH(self):
    dt = datetime.datetime(1999, 12, 31, 23, 59, 58, 999999, tzinfo=OTH())
    self.assertEqual("1999-12-31T23:59:58.999999+01:00",
                     cwmpdate.cwmpformat(dt))


if __name__ == '__main__':
  unittest.main()

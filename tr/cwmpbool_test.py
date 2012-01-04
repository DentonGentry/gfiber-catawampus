#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for cwmpboolean.py"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import cwmpbool
import unittest

class CwmpDateTest(unittest.TestCase):
  """Tests for boolean formatting."""

  def testParse(self):
    self.assertTrue(cwmpbool.parse("true"))
    self.assertTrue(cwmpbool.parse("True"))
    self.assertTrue(cwmpbool.parse("1"))
    self.assertFalse(cwmpbool.parse("false"))
    self.assertFalse(cwmpbool.parse("False"))
    self.assertFalse(cwmpbool.parse("0"))

  def testFormat(self):
    self.assertEqual(cwmpbool.format(True), "1")
    self.assertEqual(cwmpbool.format(False), "0")

if __name__ == '__main__':
  unittest.main()

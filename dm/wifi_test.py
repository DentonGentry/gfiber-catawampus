#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for wifi.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import stat
import tempfile
import unittest

import google3
import wifi


class WifiTest(unittest.TestCase):
  def testContiguousRanges(self):
    self.assertEqual(wifi.ContiguousRanges([1, 2, 3, 4, 5]), '1-5')
    self.assertEqual(wifi.ContiguousRanges([1, 2, 3, 5]), '1-3,5')
    self.assertEqual(wifi.ContiguousRanges([1, 2, 3, 5, 6, 7]), '1-3,5-7')
    self.assertEqual(wifi.ContiguousRanges([1, 2, 3, 5, 7, 8, 9]), '1-3,5,7-9')
    self.assertEqual(wifi.ContiguousRanges([1, 3, 5, 7, 9]), '1,3,5,7,9')


if __name__ == '__main__':
  unittest.main()

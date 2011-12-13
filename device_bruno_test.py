#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for device_bruno."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import unittest
import device_bruno

class DeviceBrunoTest(unittest.TestCase):
  """Tests for device_bruno.py."""

  def testGetSerialNumber(self):
    old_hnvram = device_bruno.HNVRAM
    device_bruno.HNVRAM = "testdata/device_bruno/hnvramFOO"
    self.assertEqual(device_bruno.GetNvramParam("FOO"), "123456789")
    device_bruno.HNVRAM = "testdata/device_bruno/hnvramFOO_Empty"
    # We deliberately check against an emtpy string, not assertFalse().
    # Returning None is not acceptable, we want a string.
    self.assertEqual(device_bruno.GetNvramParam("FOO"), '')
    device_bruno.HNVRAM = "testdata/device_bruno/hnvramFOO_Err"
    self.assertEqual(device_bruno.GetNvramParam("FOO"), '')

    device_bruno.HNVRAM = "testdata/device_bruno/hnvramFOO_Empty"
    self.assertEqual(device_bruno.GetNvramParam("FOO", "default"), 'default')
    device_bruno.HNVRAM = "testdata/device_bruno/hnvramFOO_Err"
    self.assertEqual(device_bruno.GetNvramParam("FOO", "default"), 'default')

    device_bruno.HNVRAM = old_hnvram


if __name__ == '__main__':
  unittest.main()

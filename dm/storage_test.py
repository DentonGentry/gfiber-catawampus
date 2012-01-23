#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for storage.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import fix_path

import collections
import storage
import unittest

statvfsstruct = collections.namedtuple('statvfs', ('f_bsize f_frsize f_blocks f_bfree f_bavail f_files f_ffree f_favail f_flag f_namemax'))
teststatvfs = statvfsstruct(
    f_bsize=4096, f_frsize=512, f_blocks=1024, f_bfree=512, f_bavail=498,
    f_files=1099, f_ffree=1092, f_favail=1050, f_flag=0, f_namemax=256)

def OsStatVfs(self):
  return teststatvfs


class StorageTest(unittest.TestCase):
  def setUp(self):
    storage.STATVFS = OsStatVfs

  def DISABLEDtestValidateExports(self):
    stor = storage.LogicalVolumeLinux26("/fakepath")
    stor.ValidateExports()

  def testCapacity(self):
    stor = storage.LogicalVolumeLinux26("/fakepath")
    expected = str(teststatvfs.f_bsize * teststatvfs.f_blocks)
    self.assertEqual(stor.Capacity, expected)

  def testUsedSpace(self):
    stor = storage.LogicalVolumeLinux26("/fakepath")
    used = (teststatvfs.f_blocks - teststatvfs.f_bavail) * teststatvfs.f_bsize
    self.assertEqual(stor.UsedSpace, str(used))


if __name__ == '__main__':
  unittest.main()

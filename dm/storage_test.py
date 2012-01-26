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

def OsStatVfs(rootpath):
  teststatvfs = dict()
  teststatvfs["/fakepath"] = statvfsstruct(
      f_bsize=4096, f_frsize=512, f_blocks=1024, f_bfree=512, f_bavail=498,
      f_files=1099, f_ffree=1092, f_favail=1050, f_flag=0, f_namemax=256)
  teststatvfs["/"] = statvfsstruct(
      f_bsize=4096, f_frsize=512, f_blocks=2048, f_bfree=100, f_bavail=120,
      f_files=2000, f_ffree=1000, f_favail=850, f_flag=0, f_namemax=256)
  teststatvfs["/tmp"] = statvfsstruct(
      f_bsize=8192, f_frsize=512, f_blocks=4096, f_bfree=1002, f_bavail=1202,
      f_files=9000, f_ffree=5000, f_favail=4000, f_flag=0, f_namemax=256)
  teststatvfs["/foo"] = statvfsstruct(
      f_bsize=2048, f_frsize=256, f_blocks=8192, f_bfree=5017, f_bavail=3766,
      f_files=6000, f_ffree=4000, f_favail=3000, f_flag=0, f_namemax=256)
  return teststatvfs[rootpath]


class StorageTest(unittest.TestCase):
  def setUp(self):
    storage.STATVFS = OsStatVfs

  def testValidateExports(self):
    stor = storage.LogicalVolumeLinux26("/fakepath", "fstype")
    stor.ValidateExports()

  def testCapacity(self):
    stor = storage.LogicalVolumeLinux26("/fakepath", "fstype")
    teststatvfs = OsStatVfs("/fakepath")
    expected = str(teststatvfs.f_bsize * teststatvfs.f_blocks)
    self.assertEqual(stor.Capacity, expected)

  def testUsedSpace(self):
    stor = storage.LogicalVolumeLinux26("/fakepath", "fstype")
    teststatvfs = OsStatVfs("/fakepath")
    used = (teststatvfs.f_blocks - teststatvfs.f_bavail) * teststatvfs.f_bsize
    self.assertEqual(stor.UsedSpace, str(used))

  def testLogicalVolumeList(self):
    storage.PROC_MOUNTS = "testdata/storage/proc.mounts"
    service = storage.StorageServiceLinux26()
    volumes = service.LogicalVolumeList
    self.assertEqual(len(volumes), 3)


if __name__ == '__main__':
  unittest.main()

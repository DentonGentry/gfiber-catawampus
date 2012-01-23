#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-140 Storage Services objects. """

__author__ = 'dgentry@google.com (Denton Gentry)'


import os
import tr.core
import tr.tr140_v1_1

BASE98STORAGE = tr.tr140_v1_1.StorageService_v1_1.StorageService

# Unit tests can override these
STATVFS = os.statvfs

class LogicalVolumeLinux26(BASE98STORAGE.LogicalVolume):
  def __init__(self, rootpath):
    BASE98STORAGE.LogicalVolume.__init__(self)
    self.rootpath = rootpath
    self.Unexport('Encrypted')
    self.Unexport('ThresholdLimit')
    self.Unexport('ThresholdReached')

  @property
  def Name(self):
    return self.rootpath

  @property
  def Enable(self):
    return True

  # TODO(dgentry) need @sessioncache decorator
  def _GetStatVfs(self):
    return STATVFS(self.rootpath)

  @property
  def Capacity(self):
    vfs = self._GetStatVfs()
    return str(vfs.f_blocks * vfs.f_bsize)

  @property
  def UsedSpace(self):
    vfs = self._GetStatVfs()
    b_used = vfs.f_blocks - vfs.f_bavail
    return str(b_used * vfs.f_bsize)

  @property
  def FolderNumberOfEntries(self):
    return 0


def main():
  pass

if __name__ == '__main__':
  main()

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
PROC_MOUNTS = "/proc/mounts"

class LogicalVolumeLinux26(BASE98STORAGE.LogicalVolume):
  def __init__(self, rootpath, fstype):
    BASE98STORAGE.LogicalVolume.__init__(self)
    self.rootpath = rootpath
    self.fstype = fstype
    self.Unexport('Encrypted')
    self.Unexport('ThresholdLimit')
    self.Unexport('ThresholdReached')
    self.Unexport('PhysicalReference')

    self.FolderList = {}

  @property
  def Name(self):
    return self.rootpath

  @property
  def Status(self):
    return "Online"

  @property
  def Enable(self):
    return True

  @property
  def FileSystem(self):
    return self.fstype

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
    return len(self.FolderList)


class StorageServiceLinux26(BASE98STORAGE):
  """Implements tr-140 for Linux 2.6-ish systems."""
  def __init__(self):
    BASE98STORAGE.__init__(self)
    self.PhysicalMediumList = {}
    self.StorageArrayList = {}
    self.LogicalVolumeList = tr.core.AutoDict(
        'LogicalVolumeList', iteritems=self.IterLogicalVolumes,
        getitem=self.GetLogicalVolumeByIndex)
    self.UserAccountList = {}
    self.UserGroupList = {}

  # Filesystems which are not interesting to export to the ACS
  SILLY = frozenset(['devtmpfs', 'proc', 'sysfs', 'usbfs', 'devpts',
      'rpc_pipefs', 'autofs', 'nfsd', 'binfmt_misc'])

  @property
  def Enable(self):
    # TODO: tr-140 says this is supposed to be writable, and disable filesystems
    return cwmpbool.format(True)

  @property
  def PhysicalMediumNumberOfEntries(self):
    return len(self.PhysicalMediumList)

  @property
  def StorageArrayNumberOfEntries(self):
    return len(self.StorageArrayList)

  @property
  def LogicalVolumeNumberOfEntries(self):
    return len(self.LogicalVolumeList)

  @property
  def UserAccountNumberOfEntries(self):
    return len(self.UserAccountList)

  @property
  def UserGroupNumberOfEntries(self):
    return len(self.UserGroupList)

  def _ParseProcMounts(self):
    """Return list of (mount point, filesystem type) tuples."""
    mounts = dict()
    try:
      f = open(PROC_MOUNTS)
    except IOError:
      return []
    for line in f:
      fields = line.split()
      # ex: /dev/mtdblock9 / squashfs ro,relatime 0 0
      if len(fields) < 6:
        continue
      fsname = fields[0]
      mountpoint = fields[1]
      fstype = fields[2]
      if fsname == "none" or fstype in self.SILLY:
        continue
      mounts[mountpoint] = fstype
    return sorted(mounts.items())

  def GetLogicalVolume(self, fstuple):
    """Get an LogicalVolume object for a mounted filesystem."""
    (mountpoint, fstype) = fstuple
    return LogicalVolumeLinux26(mountpoint, fstype)

  def IterLogicalVolumes(self):
    """Retrieves a list of all mounted filesystems."""
    fstuples = self._ParseProcMounts()
    for idx, fstuple in enumerate(fstuples):
      yield idx, self.GetLogicalVolume(fstuple)

  def GetLogicalVolumeByIndex(self, index):
    fstuples = self._ParseProcMounts()
    return self.GetLogicalVolume(fstuples[index])



def main():
  pass

if __name__ == '__main__':
  main()

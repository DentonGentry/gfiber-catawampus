#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-140 Storage Services objects."""

__author__ = 'dgentry@google.com (Denton Gentry)'


import os
import tr.core
import tr.tr140_v1_1

BASESTORAGE = tr.tr140_v1_1.StorageService_v1_1.StorageService

# Unit tests can override these
STATVFS = os.statvfs
PROC_MOUNTS = '/proc/mounts'
PROC_FILESYSTEMS = '/proc/filesystems'


def _FsType(fstype):
  supported = {'vfat': 'FAT32', 'ext2': 'ext2', 'ext3': 'ext3',
               'ext4': 'ext4', 'msdos': 'FAT32', 'xfs': 'xfs',
               'reiserfs': 'REISER'}
  if fstype in supported:
    return supported[fstype]
  else:
    return 'X_GOOGLE-COM_' + fstype


def _IsSillyFilesystem(fstype):
  """Filesystems which are not interesting to export to the ACS."""
  SILLY = frozenset(['devtmpfs', 'proc', 'sysfs', 'usbfs', 'devpts',
                     'rpc_pipefs', 'autofs', 'nfsd', 'binfmt_misc', 'fuseblk'])
  return fstype in SILLY


class LogicalVolumeLinux26(BASESTORAGE.LogicalVolume):
  """Implementation of tr-140 StorageService.LogicalVolume for Linux FS."""

  def __init__(self, rootpath, fstype):
    BASESTORAGE.LogicalVolume.__init__(self)
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
    return 'Online'

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
    return vfs.f_blocks * vfs.f_bsize

  @property
  def UsedSpace(self):
    vfs = self._GetStatVfs()
    b_used = vfs.f_blocks - vfs.f_bavail
    return b_used * vfs.f_bsize

  @property
  def FolderNumberOfEntries(self):
    return len(self.FolderList)


class CapabilitiesNoneLinux26(BASESTORAGE.Capabilities):
  """Trivial tr-140 StorageService.Capabilities, all False."""

  def __init__(self):
    BASESTORAGE.Capabilities.__init__(self)

  @property
  def FTPCapable(self):
    return False

  @property
  def HTTPCapable(self):
    return False

  @property
  def HTTPSCapable(self):
    return False

  @property
  def HTTPWritable(self):
    return False

  @property
  def SFTPCapable(self):
    return False

  @property
  def SupportedFileSystemTypes(self):
    """Returns possible filesystems.

    Parses /proc/filesystems, omit any defined as uninteresting in
    _IsSillyFileSystem(), and return the rest.

    Returns:
      a string of comma-separated filesystem types.
    """
    fslist = set()
    f = open(PROC_FILESYSTEMS)
    for line in f:
      if line.find('nodev') >= 0:
        # rule of thumb to skip internal, non-interesting filesystems
        continue
      fstype = line.strip()
      if _IsSillyFilesystem(fstype):
        continue
      fslist.add(_FsType(fstype))
    return ','.join(sorted(fslist, key=str.lower))

  @property
  def SupportedNetworkProtocols(self):
    return ''

  @property
  def SupportedRaidTypes(self):
    return ''

  @property
  def VolumeEncryptionCapable(self):
    return False


class StorageServiceLinux26(BASESTORAGE):
  """Implements a basic tr-140 for Linux 2.6-ish systems.

  This class implements no network file services, it only exports
  the LogicalVolume information.
  """

  def __init__(self):
    BASESTORAGE.__init__(self)
    self.Capabilities = CapabilitiesNoneLinux26()
    self.Unexport(objects='NetInfo')
    self.Unexport(objects='NetworkServer')
    self.Unexport(objects='FTPServer')
    self.Unexport(objects='SFTPServer')
    self.Unexport(objects='HTTPServer')
    self.Unexport(objects='HTTPSServer')
    self.PhysicalMediumList = {}
    self.StorageArrayList = {}
    self.LogicalVolumeList = tr.core.AutoDict(
        'LogicalVolumeList', iteritems=self.IterLogicalVolumes,
        getitem=self.GetLogicalVolumeByIndex)
    self.UserAccountList = {}
    self.UserGroupList = {}

  @property
  def Enable(self):
    # TODO(dgentry): tr-140 says this is supposed to be writable
    return True

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
      if fsname == 'none' or _IsSillyFilesystem(fstype):
        continue
      mounts[mountpoint] = _FsType(fstype)
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

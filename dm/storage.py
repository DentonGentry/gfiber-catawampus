#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-140 Storage Services objects."""

__author__ = 'dgentry@google.com (Denton Gentry)'


import os
import re
import subprocess
import tr.core
import tr.tr140_v1_1

BASESTORAGE = tr.tr140_v1_1.StorageService_v1_1.StorageService

# Unit tests can override these
PROC_FILESYSTEMS = '/proc/filesystems'
PROC_MOUNTS = '/proc/mounts'
SLASHDEV = '/dev/'
SMARTCTL = '/usr/sbin/smartctl'
STATVFS = os.statvfs
SYS_BLOCK = '/sys/block/'


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


class PhysicalMediumDiskLinux26(BASESTORAGE.PhysicalMedium):
  """tr-140 PhysicalMedium implementation for non-removable disks."""

  CONNECTION_TYPES = frozenset(
      ['USB 1.1', 'USB 2.0', 'IEEE1394', 'IEEE1394b', 'IDE', 'EIDE',
       'ATA/33', 'ATA/66', 'ATA/100', 'ATA/133', 'SATA/150', 'SATA/300',
       'SCSI-1', 'Fast SCSI', 'Fast-Wide SCSI', 'Ultra SCSI', 'Ultra Wide SCSI',
       'Ultra2 SCSI', 'Ultra2 Wide SCSI', 'Ultra3 SCSI', 'Ultra-320 SCSI',
       'Ultra-640 SCSI', 'SSA', 'SSA-40', 'Fibre Channel'])

  def __init__(self, dev, conn_type=None):
    BASESTORAGE.PhysicalMedium.__init__(self)
    self.dev = dev
    self.name = dev

    if conn_type is None:
      # transport is really, really hard to infer programatically.
      # If platform code doesn't provide it, don't try to guess.
      self.Unexport('ConnectionType')
    else:
      # Provide a hint to the platform code: use a valid enumerated string,
      # or define a vendor extension. Don't just make something up.
      assert conn_type[0:1] == 'X_' or conn_type in self.CONNECTION_TYPES
    self.conn_type = conn_type

    # TODO(dgentry) read SMART attribute for PowerOnHours
    self.Unexport('Uptime')

    # TODO(dgentry) What does 'Standby' or 'Offline' mean?
    self.Unexport('Status')

  def _ReadOneLine(self, filename, default):
    """Read one line from a file. Return default if anything fails."""
    try:
      f = open(filename, 'r')
      return f.readline().strip()
    except IOError:
      return default

  # TODO(dgentry) need @sessioncache decorator
  def _GetSmartctlOutput(self):
    """Return smartctl info and health output."""
    dev = SLASHDEV + self.dev
    smart = subprocess.Popen([SMARTCTL, '--info', '--health', dev],
                             stdout=subprocess.PIPE)
    out, _ = smart.communicate(None)
    return out

  def _GetFieldFromSmartctl(self, prefix, default=''):
    """Search smartctl output for line of the form 'Foo: Bar', return 'Bar'."""
    field_re = re.compile(prefix + '\s*(\S+)')
    out = self._GetSmartctlOutput().splitlines()
    for line in out:
      result = field_re.search(line)
      if result is not None:
        return result.group(1).strip()
    return default

  def GetName(self):
    return self.name

  def SetName(self, value):
    self.name = value

  Name = property(GetName, SetName, None, 'PhysicalMedium.Name')

  @property
  def Vendor(self):
    filename = SYS_BLOCK + '/' + self.dev + '/device/vendor'
    vendor = self._ReadOneLine(filename=filename, default='')
    # /sys/block/?da/device/vendor is often 'ATA'. Not useful.
    return '' if vendor == 'ATA' else vendor

  @property
  def Model(self):
    filename = SYS_BLOCK + '/' + self.dev + '/device/model'
    return self._ReadOneLine(filename=filename, default='')

  @property
  def SerialNumber(self):
    return self._GetFieldFromSmartctl('Serial Number:')

  @property
  def FirmwareVersion(self):
    return self._GetFieldFromSmartctl('Firmware Version:')

  @property
  def ConnectionType(self):
    return self.conn_type

  @property
  def Removable(self):
    return False

  @property
  def Capacity(self):
    """Return capacity in Megabytes."""
    filename = SYS_BLOCK + '/' + self.dev + '/size'
    size = self._ReadOneLine(filename=filename, default='0')
    try:
      # TODO(dgentry) Do 4k sector drives populate size in 512 byte blocks?
      return int(size) * 512 / 1048576
    except ValueError:
      return 0

  @property
  def SMARTCapable(self):
    capable = self._GetFieldFromSmartctl('SMART support is: Enab', default=None)
    return True if capable else False

  @property
  def Health(self):
    health = self._GetFieldFromSmartctl(
        'SMART overall-health self-assessment test result:')
    if health == 'PASSED':
      return 'OK'
    elif health.find('FAIL') >= 0:
      return 'Failing'
    else:
      return 'Error'

  @property
  def HotSwappable(self):
    filename = SYS_BLOCK + '/' + self.dev + '/removable'
    removable = self._ReadOneLine(filename=filename, default='0').strip()
    return False if removable == '0' else True


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
    if index >= len(fstuples):
      raise IndexError('No such object LogicalVolume.{0}'.format(index))
    return self.GetLogicalVolume(fstuples[index])


def main():
  pass

if __name__ == '__main__':
  main()

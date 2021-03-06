#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# unittest requires method names starting in 'test'
# pylint:disable=invalid-name

"""Unit tests for storage.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import collections
import google3
from tr.wvtest import unittest
import tr.handle
import tr.session
import storage


statvfsstruct = collections.namedtuple(
    'statvfs', ('f_bsize f_frsize f_blocks f_bfree f_bavail f_files f_ffree '
                'f_favail f_flag f_namemax'))
test_mtdpath = ''


def OsStatVfs(rootpath):
  if rootpath == '/raise_os_error':
    raise OSError('If you see this, the test fails.')
  teststatvfs = dict()
  teststatvfs['/fakepath'] = statvfsstruct(
      f_bsize=4096, f_frsize=512, f_blocks=1024, f_bfree=512, f_bavail=498,
      f_files=1099, f_ffree=1092, f_favail=1050, f_flag=0, f_namemax=256)
  teststatvfs['/'] = statvfsstruct(
      f_bsize=4096, f_frsize=512, f_blocks=2048, f_bfree=100, f_bavail=120,
      f_files=2000, f_ffree=1000, f_favail=850, f_flag=0, f_namemax=256)
  teststatvfs['/tmp'] = statvfsstruct(
      f_bsize=8192, f_frsize=512, f_blocks=4096, f_bfree=1002, f_bavail=1202,
      f_files=9000, f_ffree=5000, f_favail=4000, f_flag=0, f_namemax=256)
  teststatvfs['/foo'] = statvfsstruct(
      f_bsize=2048, f_frsize=256, f_blocks=8192, f_bfree=5017, f_bavail=3766,
      f_files=6000, f_ffree=4000, f_favail=3000, f_flag=0x0001, f_namemax=256)
  return teststatvfs[rootpath]


def GetMtdStats(mtdpath):
  global test_mtdpath
  test_mtdpath = mtdpath
  return storage.MtdEccStats(corrected=10, failed=20,
                             badblocks=30, bbtblocks=40)


class StorageTest(unittest.TestCase):

  def setUp(self):
    self.old_DISKSTAT = storage.DISKSTAT
    self.old_GETMTDSTATS = storage.GETMTDSTATS
    self.old_PROC_FILESYSTEMS = storage.PROC_FILESYSTEMS
    self.old_PROC_MOUNTS = storage.PROC_MOUNTS
    self.old_SMARTCTL = storage.SMARTCTL
    self.old_STATVFS = storage.STATVFS
    self.old_SYS_BLOCK = storage.SYS_BLOCK
    self.old_SYS_UBI = storage.SYS_UBI
    storage.DISKSTAT = 'testdata/storage/sys/'
    storage.GETMTDSTATS = GetMtdStats
    storage.SMARTCTL = 'testdata/storage/smartctl'
    storage.STATVFS = OsStatVfs
    storage.SYS_UBI = 'testdata/storage/sys/class'
    tr.session.cache.flush()

  def tearDown(self):
    storage.DISKSTAT = self.old_DISKSTAT
    storage.GETMTDSTATS = self.old_GETMTDSTATS
    storage.PROC_FILESYSTEMS = self.old_PROC_FILESYSTEMS
    storage.PROC_MOUNTS = self.old_PROC_MOUNTS
    storage.SMARTCTL = self.old_SMARTCTL
    storage.STATVFS = self.old_STATVFS
    storage.SYS_BLOCK = self.old_SYS_BLOCK
    storage.SYS_UBI = self.old_SYS_UBI

  def testValidateExports(self):
    storage.PROC_FILESYSTEMS = 'testdata/storage/proc.filesystems'
    storage.PROC_MOUNTS = 'testdata/storage/proc.mounts'
    storage.SYS_BLOCK = 'testdata/storage/sys/block'
    service = storage.StorageServiceLinux26()
    tr.handle.ValidateExports(service)
    stor = storage.LogicalVolumeLinux26('/fakepath', 'fstype')
    tr.handle.ValidateExports(stor)
    pm = storage.PhysicalMediumDiskLinux26('sda')
    tr.handle.ValidateExports(pm)

  def testLogicalVolumeCapacity(self):
    stor = storage.LogicalVolumeLinux26('/fakepath', 'fstype')
    teststatvfs = OsStatVfs('/fakepath')
    expected = teststatvfs.f_bsize * teststatvfs.f_blocks / 1024 / 1024
    self.assertEqual(stor.Capacity, expected)

  def testUsedSpace(self):
    stor = storage.LogicalVolumeLinux26('/fakepath', 'fstype')
    teststatvfs = OsStatVfs('/fakepath')
    used = (teststatvfs.f_blocks - teststatvfs.f_bavail) * teststatvfs.f_bsize
    self.assertEqual(stor.UsedSpace, used / 1024 / 1024)

  def testLogicalVolumeThresholdReached(self):
    stor = storage.LogicalVolumeLinux26('/fakepath', 'fstype')
    stor.ThresholdLimit = 1
    self.assertFalse(stor.ThresholdReached)
    stor.ThresholdLimit = 4
    self.assertTrue(stor.ThresholdReached)

  def testLogicalVolumeList(self):
    storage.PROC_MOUNTS = 'testdata/storage/proc.mounts'
    service = storage.StorageServiceLinux26()
    volumes = service.LogicalVolumeList
    self.assertEqual(len(volumes), 3)
    self.assertEqual(service.LogicalVolumeNumberOfEntries, 3)
    expectedFs = {'/': 'X_CATAWAMPUS-ORG_squashfs',
                  '/foo': 'X_CATAWAMPUS-ORG_ubifs',
                  '/tmp': 'X_CATAWAMPUS-ORG_tmpfs'}
    expectedRo = {'/': False, '/foo': True, '/tmp': False}
    found = set()
    for vol in volumes.values():
      found.add(vol.Name)
      t = OsStatVfs(vol.Name)
      self.assertEqual(vol.Status, 'Online')
      self.assertTrue(vol.Enable)
      self.assertEqual(vol.FileSystem, expectedFs[vol.Name])
      self.assertEqual(vol.Capacity, t.f_bsize * t.f_blocks / 1024 / 1024)
      expected = t.f_bsize * (t.f_blocks - t.f_bavail) / 1024 / 1024
      self.assertEqual(vol.UsedSpace, expected)
      self.assertEqual(vol.X_CATAWAMPUS_ORG_ReadOnly, expectedRo[vol.Name])
    self.assertEqual(found, set(expectedFs.keys()))

  def testCapabilitiesNone(self):
    storage.PROC_FILESYSTEMS = 'testdata/storage/proc.filesystems'
    cap = storage.CapabilitiesNoneLinux26()
    tr.handle.ValidateExports(cap)
    self.assertFalse(cap.FTPCapable)
    self.assertFalse(cap.HTTPCapable)
    self.assertFalse(cap.HTTPSCapable)
    self.assertFalse(cap.HTTPWritable)
    self.assertFalse(cap.SFTPCapable)
    self.assertEqual(cap.SupportedNetworkProtocols, '')
    self.assertEqual(cap.SupportedRaidTypes, '')
    self.assertFalse(cap.VolumeEncryptionCapable)

  def testCapabilitiesNoneFsTypes(self):
    storage.PROC_FILESYSTEMS = 'testdata/storage/proc.filesystems'
    cap = storage.CapabilitiesNoneLinux26()
    self.assertEqual(
        cap.SupportedFileSystemTypes,
        'ext2,ext3,ext4,FAT32,X_CATAWAMPUS-ORG_iso9660,'
        'X_CATAWAMPUS-ORG_squashfs,X_CATAWAMPUS-ORG_tmpfs,X_CATAWAMPUS-ORG_udf')

  def testPhysicalMediumName(self):
    pm = storage.PhysicalMediumDiskLinux26('sda')
    self.assertEqual(pm.Name, 'sda')
    pm.Name = 'sdb'
    self.assertEqual(pm.Name, 'sdb')

  def testPhysicalMediumFields(self):
    storage.SYS_BLOCK = 'testdata/storage/sys/block'
    pm = storage.PhysicalMediumDiskLinux26('sda')
    self.assertEqual(pm.Vendor, 'vendor_name')
    self.assertEqual(pm.Model, 'model_name')
    self.assertEqual(pm.SerialNumber, 'serial_number')
    self.assertEqual(pm.FirmwareVersion, 'firmware_version')
    self.assertTrue(pm.SMARTCapable)
    self.assertEqual(pm.Health, 'OK')
    self.assertFalse(pm.Removable)
    self.assertEqual(pm.Uptime, 90)

  def testNotSmartCapable(self):
    storage.SMARTCTL = 'testdata/storage/smartctl_disabled'
    storage.SYS_BLOCK = 'testdata/storage/sys/block'
    pm = storage.PhysicalMediumDiskLinux26('sda')
    self.assertFalse(pm.SMARTCapable)

  def testHealthFailing(self):
    storage.SMARTCTL = 'testdata/storage/smartctl_healthfail'
    storage.SYS_BLOCK = 'testdata/storage/sys/block'
    pm = storage.PhysicalMediumDiskLinux26('sda')
    self.assertEqual(pm.Health, 'Failing')

  def testHealthError(self):
    storage.SMARTCTL = 'testdata/storage/smartctl_healtherr'
    storage.SYS_BLOCK = 'testdata/storage/sys/block'
    pm = storage.PhysicalMediumDiskLinux26('sda')
    self.assertEqual(pm.Health, 'Error')

  def testPhysicalMediumVendorATA(self):
    storage.SYS_BLOCK = 'testdata/storage/sys/block_ATA'
    pm = storage.PhysicalMediumDiskLinux26('sda')
    # vendor 'ATA' is suppressed, as it is useless
    self.assertEqual(pm.Vendor, '')

  def testPhysicalMediumCapacity(self):
    storage.SYS_BLOCK = 'testdata/storage/sys/block'
    pm = storage.PhysicalMediumDiskLinux26('sda')
    self.assertEqual(pm.Capacity, 512)

  def testPhysicalMediumConnType(self):
    storage.SYS_BLOCK = 'testdata/storage/sys/block'
    pm = storage.PhysicalMediumDiskLinux26('sda', conn_type='IDE')
    self.assertEqual(pm.ConnectionType, 'IDE')
    self.assertRaises(AssertionError, storage.PhysicalMediumDiskLinux26,
                      'sda', conn_type='NotValid')

  def testPhysicalMediumHotSwappable(self):
    storage.SYS_BLOCK = 'testdata/storage/sys/block'
    pm = storage.PhysicalMediumDiskLinux26('sda')
    self.assertFalse(pm.HotSwappable)
    storage.SYS_BLOCK = 'testdata/storage/sys/blockRemovable'
    self.assertTrue(pm.HotSwappable)

  def testFlashMedium(self):
    fm = storage.FlashMediumUbiLinux26('ubi2')
    tr.handle.ValidateExports(fm)
    self.assertEqual(fm.BadEraseBlocks, 4)
    self.assertEqual(fm.CorrectedErrors, 10)
    self.assertEqual(fm.EraseBlockSize, 1040384)
    self.assertEqual(fm.IOSize, 4096)
    self.assertEqual(fm.MaxEraseCount, 3)
    self.assertEqual(fm.Name, 'ubi2')
    self.assertEqual(fm.ReservedEraseBlocks, 10)
    self.assertEqual(fm.TotalEraseBlocks, 508)
    self.assertEqual(fm.UncorrectedErrors, 20)

  def testFlashSubVolume(self):
    sv = storage.FlashSubVolUbiLinux26('ubi2_0')
    tr.handle.ValidateExports(sv)
    self.assertEqual(sv.DataMBytes, 370)
    self.assertEqual(sv.Name, 'subvol0')
    self.assertEqual(sv.Status, 'OK')
    sv = storage.FlashSubVolUbiLinux26('ubi2_1')
    tr.handle.ValidateExports(sv)
    self.assertEqual(sv.DataMBytes, 56)
    self.assertEqual(sv.Name, 'subvol1')
    self.assertEqual(sv.Status, 'Corrupted')

  def testAttributes(self):
    attr = storage.SmartAttributes('sda')
    tr.handle.ValidateExports(attr)
    self.assertEqual(attr.RawReadErrorRate, 10)
    self.assertEqual(attr.ThroughputPerformance, 20)
    self.assertEqual(attr.SpinUpTime, 35)
    self.assertEqual(attr.SpinUpTimeLatest, 30)
    self.assertEqual(attr.StartStopCount, 40)
    self.assertEqual(attr.ReallocatedSectorsCount, 50)
    self.assertEqual(attr.ReadChannelMargin, 60)
    self.assertEqual(attr.SeekErrorRate, 70)
    self.assertEqual(attr.SeekTimePerformance, 80)
    self.assertEqual(attr.PowerOnHours, 90)
    self.assertEqual(attr.SpinRetryCount, 100)
    self.assertEqual(attr.CalibrationRetryCount, 110)
    self.assertEqual(attr.PowerCycleCount, 120)
    self.assertEqual(attr.PowerOffRetractCount, 1920)
    self.assertEqual(attr.LoadCycleCount, 1930)
    self.assertEqual(attr.LoadCycleCount, 1930)
    self.assertEqual(attr.TemperatureCelsius, 1942)
    self.assertEqual(attr.TemperatureCelsiusMin, 1940)
    self.assertEqual(attr.TemperatureCelsiusMax, 1944)
    self.assertEqual(attr.HardwareEccRecovered, 1950)
    self.assertEqual(attr.ReallocatedEventCount, 1960)
    self.assertEqual(attr.CurrentPendingSector, 1970)
    self.assertEqual(attr.OfflineUncorrectable, 1980)
    self.assertEqual(attr.UdmaCrcErrorCount, 1990)
    self.assertEqual(attr.MultiZoneErrorRate, 2000)
    self.assertEqual(attr.SoftReadErrorRate, 2010)
    self.assertEqual(attr.TaIncreaseCount, 2020)
    self.assertEqual(attr.RunOutCancel, 2030)
    self.assertEqual(attr.ShockCountWriteOperation, 2040)
    self.assertEqual(attr.ShockRateWriteOperation, 2050)
    self.assertEqual(attr.FlyingHeight, 2060)
    self.assertEqual(attr.SpinHighCurrent, 2070)
    self.assertEqual(attr.SpinBuzz, 2080)
    self.assertEqual(attr.OfflineSeekPerformance, 2090)

  def testDrivePerformance(self):
    perf = storage.DrivePerformance(dev='sda')
    tr.handle.ValidateExports(perf)
    self.assertEqual(perf.ReadsCompleted, 1)
    self.assertEqual(perf.ReadsMerged, 2)
    self.assertEqual(perf.ReadSectors, 3)
    self.assertEqual(perf.ReadMilliseconds, 4)
    self.assertEqual(perf.WritesCompleted, 5)
    self.assertEqual(perf.WritesMerged, 6)
    self.assertEqual(perf.WriteSectors, 7)
    self.assertEqual(perf.WriteMilliseconds, 8)
    self.assertEqual(perf.IoInProgress, 9)
    self.assertEqual(perf.IoMilliseconds, 10)
    self.assertEqual(perf.WeightedIoMilliseconds, 11)

  def testSataPhy(self):
    sata = storage.SataPHY(dev='sda')
    tr.handle.ValidateExports(sata)
    self.assertEqual(sata.CmdFailedICRC, 10)
    self.assertEqual(sata.RErrDataFis, 20)
    self.assertEqual(sata.RErrDeviceToHostDataFis, 30)
    self.assertEqual(sata.RErrHostToDeviceDataFis, 40)
    self.assertEqual(sata.RErrNonDataFis, 50)
    self.assertEqual(sata.RErrDeviceToHostNonDataFis, 60)
    self.assertEqual(sata.RErrHostToDeviceNonDataFis, 70)
    self.assertEqual(sata.DeviceToHostNonDataRetries, 80)
    self.assertEqual(sata.PhyRdyToPhyNRdy, 90)
    self.assertEqual(sata.RegisterFisComreset, 100)
    self.assertEqual(sata.HostToDeviceCrcErrors, 110)
    self.assertEqual(sata.HostToDeviceNonCrcErrors, 130)
    self.assertEqual(sata.RErrHostToDeviceDataFisCrc, 150)
    self.assertEqual(sata.RErrHostToDeviceDataFisNonCrc, 160)
    self.assertEqual(sata.RErrHostToDeviceNonDataFisCrc, 180)
    self.assertEqual(sata.RErrHostToDeviceNonDataFisNonCrc, 190)

  def testOsError(self):
    stor = storage.LogicalVolumeLinux26('/raise_os_error', 'fstype')
    self.assertEqual(stor.Capacity, 0)


if __name__ == '__main__':
  unittest.main()

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

# TR-069 has mandatory attribute names that don't comply with policy
# pylint: disable-msg=C6409

"""Implementation of tr-140 Storage Services objects."""

__author__ = 'dgentry@google.com (Denton Gentry)'


import ctypes
import fcntl
import os
import os.path
import re
import subprocess
import tr.core
import tr.session
import tr.tr140_v1_1
import tr.types
import tr.x_catawampus_storage_1_0


CATASTORAGE = tr.x_catawampus_storage_1_0.X_CATAWAMPUS_ORG_Storage_v1_0
BASESTORAGE = CATASTORAGE.StorageService
PHYSICALMEDIUM = BASESTORAGE.PhysicalMedium
DISKSTAT = '/sys/block/'

# Example: 0x0001  2            0  Command failed due to ICRC error
SATAPHY = re.compile(r'^(?P<reg>\S+)\s+\d+\s+(?P<val>\d+)\s+')

# Example: 1 Raw_Read_Error_Rate 0x000b 100 100 016 Pre-fail Always - 10
SMARTATTR = re.compile(r'^\s*(\d+)\s+(?P<attr>\S+)\s+\S+\s+\d+\s+\d+\s+\d+'
                       r'\s+\S+\s+\S+\s+\S+\s+(?P<val>\d+)\s*'
                       r'(\(Average (?P<average>\d+)\)|'
                       r'\(Min/Max (?P<min>\d+)/(?P<max>\d+)\))?')


class MtdEccStats(ctypes.Structure):
  """<mtd/mtd-abi.h> struct mtd_ecc_stats."""

  _fields_ = [('corrected', ctypes.c_uint32),
              ('failed', ctypes.c_uint32),
              ('badblocks', ctypes.c_uint32),
              ('bbtblocks', ctypes.c_uint32)]


def _GetMtdStats(mtddev):
  """Return the MtdEccStats for the given mtd device.

  Arguments:
    mtddev: the string path to the device, ex: '/dev/mtd14'
  Raises:
    IOError: if the ioctl fails.
  Returns:
    an MtdEccStats.
  """

  ECCGETSTATS = 0x40104d12  # ECCGETSTATS _IOR('M', 18, struct mtd_ecc_stats)
  with open(mtddev, 'r') as f:
    ecc = MtdEccStats()
    if fcntl.ioctl(f, ECCGETSTATS, ctypes.addressof(ecc)) != 0:
      raise IOError('ECCGETSTATS failed')
    return ecc


# Unit tests can override these
GETMTDSTATS = _GetMtdStats
PROC_FILESYSTEMS = '/proc/filesystems'
PROC_MOUNTS = '/proc/mounts'
SLASHDEV = '/dev/'
SMARTCTL = 'smartctl'
STATVFS = os.statvfs
SYS_BLOCK = '/sys/block/'
SYS_UBI = '/sys/class/ubi/'


def _FsType(fstype):
  supported = {'vfat': 'FAT32', 'ext2': 'ext2', 'ext3': 'ext3',
               'ext4': 'ext4', 'msdos': 'FAT32', 'xfs': 'xfs',
               'reiserfs': 'REISER'}
  if fstype in supported:
    return supported[fstype]
  else:
    return 'X_CATAWAMPUS-ORG_' + fstype


def _IsSillyFilesystem(fstype):
  """Filesystems which are not interesting to export to the ACS."""
  SILLY = frozenset(['devtmpfs', 'proc', 'sysfs', 'usbfs', 'devpts',
                     'rpc_pipefs', 'autofs', 'nfsd', 'binfmt_misc', 'fuseblk'])
  return fstype in SILLY


def _GetFieldFromOutput(prefix, output, default=''):
  """Search output for line of the form 'Foo: Bar', return 'Bar'."""
  field_re = re.compile(prefix + r'\s*(\S+)')
  for line in output.splitlines():
    result = field_re.search(line)
    if result is not None:
      return result.group(1).strip()
  return default


def _ReadOneLine(filename, default):
  """Read one line from a file. Return default if anything fails."""
  try:
    with open(filename) as f:
      return f.readline().strip()
  except IOError:
    return default


def IntFromFile(filename):
  """Read one line from a file and return an int, or zero if an error occurs."""
  try:
    buf = _ReadOneLine(filename, '0')
    return int(buf)
  except ValueError:
    return 0


def _IntOrNegativeOne(result, name):
  try:
    string = result.group(name)
    return int(str(string), base=0)
  except (ValueError, KeyError, TypeError):
    return -1


class LogicalVolumeLinux26(BASESTORAGE.LogicalVolume):
  """Implementation of tr-140 StorageService.LogicalVolume for Linux FS."""

  Enable = tr.types.ReadOnlyBool(True)
  FileSystem = tr.types.ReadOnlyString('')
  Name = tr.types.ReadOnlyString('')
  Status = tr.types.ReadOnlyString('Online')

  def __init__(self, rootpath, fstype):
    super(LogicalVolumeLinux26, self).__init__()
    type(self).Name.Set(self, rootpath)
    self.rootpath = rootpath
    type(self).FileSystem.Set(self, fstype)
    self.Unexport('Alias')
    self.Unexport('Encrypted')
    self.Unexport('ThresholdReached')
    self.Unexport('PhysicalReference')
    self.FolderList = {}
    self.ThresholdLimit = 0

  @tr.session.cache
  def _GetStatVfs(self):
    return STATVFS(self.rootpath)

  @property
  def Capacity(self):
    vfs = self._GetStatVfs()
    return int(vfs.f_blocks * vfs.f_bsize / 1024 / 1024)

  @property
  def ThresholdReached(self):
    vfs = self._GetStatVfs()
    require = self.ThresholdLimit * 1024 * 1024
    avail = vfs.f_bavail * vfs.f_bsize
    return True if avail < require else False

  @property
  def UsedSpace(self):
    vfs = self._GetStatVfs()
    b_used = vfs.f_blocks - vfs.f_bavail
    return int(b_used * vfs.f_bsize / 1024 / 1024)

  @property
  def X_CATAWAMPUS_ORG_ReadOnly(self):
    ST_RDONLY = 0x0001
    vfs = self._GetStatVfs()
    return True if vfs.f_flag & ST_RDONLY else False

  @property
  def FolderNumberOfEntries(self):
    return len(self.FolderList)


class PhysicalMediumDiskLinux26(BASESTORAGE.PhysicalMedium):
  """tr-140 PhysicalMedium implementation for non-removable disks."""

  CONNECTION_TYPES = frozenset(
      ['USB 1.1', 'USB 2.0', 'IEEE1394', 'IEEE1394b', 'IDE', 'EIDE',
       'ATA/33', 'ATA/66', 'ATA/100', 'ATA/133',
       'SATA/150', 'SATA/300', 'SATA/600',
       'SCSI-1', 'Fast SCSI', 'Fast-Wide SCSI', 'Ultra SCSI', 'Ultra Wide SCSI',
       'Ultra2 SCSI', 'Ultra2 Wide SCSI', 'Ultra3 SCSI', 'Ultra-320 SCSI',
       'Ultra-640 SCSI', 'SSA', 'SSA-40', 'Fibre Channel'])

  ConnectionType = tr.types.ReadOnlyString('')
  FirmwareVersion = tr.types.ReadOnlyString('')
  Removable = tr.types.ReadOnlyBool(False)
  SerialNumber = tr.types.ReadOnlyString('')
  SMARTCapable = tr.types.ReadOnlyBool(False)

  def __init__(self, dev, conn_type=None):
    super(PhysicalMediumDiskLinux26, self).__init__()
    self.dev = dev
    self.Name = dev
    self.Unexport('Alias')
    # TODO(dgentry) What does 'Standby' or 'Offline' mean?
    self.Unexport('Status')

    if conn_type is None:
      # transport is really, really hard to infer programatically.
      # If platform code doesn't provide it, don't try to guess.
      self.Unexport('ConnectionType')
    else:
      # Provide a hint to the platform code: use a valid enumerated string,
      # or define a vendor extension. Don't just make something up.
      assert conn_type[0:1] == 'X_' or conn_type in self.CONNECTION_TYPES
    type(self).ConnectionType.Set(self, conn_type)
    if not conn_type or 'SATA' not in conn_type:
      self.Unexport(objects='X_CATAWAMPUS-ORG_SataPHY')

    smartctl = self._GetSmartctlOutput()
    serial = _GetFieldFromOutput(
        prefix='Serial Number:', output=smartctl, default='')
    type(self).SerialNumber.Set(self, serial)
    firmware = _GetFieldFromOutput(
        prefix='Firmware Version:', output=smartctl, default='')
    type(self).FirmwareVersion.Set(self, firmware)
    capable = _GetFieldFromOutput(
        prefix='SMART support is: Enab', output=smartctl, default=False)
    smartok = True if capable else False
    type(self).SMARTCapable.Set(self, smartok)
    if not smartok:
      self.Unexport(objects='X_CATAWAMPUS-ORG_SmartAttributes')

  @property
  def Uptime(self):
    if self.SMARTCapable:
      return self.X_CATAWAMPUS_ORG_SmartAttributes.PowerOnHours
    return 0

  @tr.session.cache
  def _GetSmartctlOutput(self):
    """Return smartctl info and health output."""
    dev = SLASHDEV + self.dev
    smart = subprocess.Popen([SMARTCTL, '--info', '--health', dev],
                             stdout=subprocess.PIPE)
    out, _ = smart.communicate(None)
    return out

  @property
  def Vendor(self):
    filename = SYS_BLOCK + '/' + self.dev + '/device/vendor'
    vendor = _ReadOneLine(filename=filename, default='')
    # /sys/block/?da/device/vendor is often 'ATA'. Not useful.
    return '' if vendor == 'ATA' else vendor

  @property
  def Model(self):
    filename = SYS_BLOCK + '/' + self.dev + '/device/model'
    return _ReadOneLine(filename=filename, default='')

  @property
  def Capacity(self):
    """Return capacity in Megabytes."""
    filename = SYS_BLOCK + '/' + self.dev + '/size'
    size = _ReadOneLine(filename=filename, default='0')
    try:
      # TODO(dgentry) Do 4k sector drives populate size in 512 byte blocks?
      return int(size) * 512 / 1048576
    except ValueError:
      return 0

  @property
  def Health(self):
    health = _GetFieldFromOutput(
        prefix='SMART overall-health self-assessment test result:',
        output=self._GetSmartctlOutput(), default='')
    if health == 'PASSED':
      return 'OK'
    elif health.find('FAIL') >= 0:
      return 'Failing'
    else:
      return 'Error'

  @property
  def HotSwappable(self):
    filename = SYS_BLOCK + '/' + self.dev + '/removable'
    removable = _ReadOneLine(filename=filename, default='0').strip()
    return False if removable == '0' else True

  @property
  def X_CATAWAMPUS_ORG_DrivePerformance(self):
    return DrivePerformance(self.dev)

  @property
  @tr.session.cache
  def X_CATAWAMPUS_ORG_SmartAttributes(self):
    return SmartAttributes(self.dev)

  @property
  @tr.session.cache
  def X_CATAWAMPUS_ORG_SataPHY(self):
    return SataPHY(self.dev)


class SmartAttributes(PHYSICALMEDIUM.X_CATAWAMPUS_ORG_SmartAttributes):
  """Catawampus Storage SMART Attributes implementation."""

  CalibrationRetryCount = tr.types.ReadOnlyInt(-1)
  CurrentPendingSector = tr.types.ReadOnlyInt(-1)
  FlyingHeight = tr.types.ReadOnlyInt(-1)
  HardwareEccRecovered = tr.types.ReadOnlyInt(-1)
  LoadCycleCount = tr.types.ReadOnlyInt(-1)
  MultiZoneErrorRate = tr.types.ReadOnlyInt(-1)
  OfflineSeekPerformance = tr.types.ReadOnlyInt(-1)
  OfflineUncorrectable = tr.types.ReadOnlyInt(-1)
  PowerCycleCount = tr.types.ReadOnlyInt(-1)
  PowerOffRetractCount = tr.types.ReadOnlyInt(-1)
  PowerOnHours = tr.types.ReadOnlyInt(-1)
  RawReadErrorRate = tr.types.ReadOnlyInt(-1)
  ReadChannelMargin = tr.types.ReadOnlyInt(-1)
  ReallocatedEventCount = tr.types.ReadOnlyInt(-1)
  ReallocatedSectorsCount = tr.types.ReadOnlyInt(-1)
  RunOutCancel = tr.types.ReadOnlyInt(-1)
  SeekErrorRate = tr.types.ReadOnlyInt(-1)
  SeekTimePerformance = tr.types.ReadOnlyInt(-1)
  ShockCountWriteOperation = tr.types.ReadOnlyInt(-1)
  ShockRateWriteOperation = tr.types.ReadOnlyInt(-1)
  SoftReadErrorRate = tr.types.ReadOnlyInt(-1)
  SpinBuzz = tr.types.ReadOnlyInt(-1)
  SpinHighCurrent = tr.types.ReadOnlyInt(-1)
  SpinRetryCount = tr.types.ReadOnlyInt(-1)
  SpinUpTime = tr.types.ReadOnlyInt(-1)
  SpinUpTimeLatest = tr.types.ReadOnlyInt(-1)
  StartStopCount = tr.types.ReadOnlyInt(-1)
  TaIncreaseCount = tr.types.ReadOnlyInt(-1)
  TemperatureCelsius = tr.types.ReadOnlyInt(-1)
  TemperatureCelsiusMax = tr.types.ReadOnlyInt(-1)
  TemperatureCelsiusMin = tr.types.ReadOnlyInt(-1)
  ThroughputPerformance = tr.types.ReadOnlyInt(-1)
  UdmaCrcErrorCount = tr.types.ReadOnlyInt(-1)

  def __init__(self, dev):
    super(SmartAttributes, self).__init__()
    self.dev = dev
    self._ParseSmartctlAttributes()

  def _ParseSmartctlAttributes(self):
    dev = SLASHDEV + self.dev
    smart = subprocess.Popen([SMARTCTL, '--attributes', dev],
                             stdout=subprocess.PIPE)
    out, _ = smart.communicate(None)
    for line in out.splitlines():
      result = SMARTATTR.search(line)
      if result is None:
        continue
      attribute = result.group('attr')
      value = _IntOrNegativeOne(result, 'val')

      if attribute == 'Calibration_Retry_Count':
        type(self).CalibrationRetryCount.Set(self, value)
      elif attribute == 'Current_Pending_Sector':
        type(self).CurrentPendingSector.Set(self, value)
      elif attribute == 'Flying_Height':
        type(self).FlyingHeight.Set(self, value)
      elif attribute == 'Hardware_ECC_Recovered':
        type(self).HardwareEccRecovered.Set(self, value)
      elif attribute == 'Load_Cycle_Count':
        type(self).LoadCycleCount.Set(self, value)
      elif attribute == 'Multi_Zone_Error_Rate':
        type(self).MultiZoneErrorRate.Set(self, value)
      elif attribute == 'Offline_Seek_Performnce':
        type(self).OfflineSeekPerformance.Set(self, value)
      elif attribute == 'Offline_Uncorrectable':
        type(self).OfflineUncorrectable.Set(self, value)
      elif attribute == 'Power_Cycle_Count':
        type(self).PowerCycleCount.Set(self, value)
      elif attribute == 'Power-Off_Retract_Count':
        type(self).PowerOffRetractCount.Set(self, value)
      elif attribute == 'Power_On_Hours':
        type(self).PowerOnHours.Set(self, value)
      elif attribute == 'Raw_Read_Error_Rate':
        type(self).RawReadErrorRate.Set(self, value)
      elif attribute == 'Read_Channel_Margin':
        type(self).ReadChannelMargin.Set(self, value)
      elif attribute == 'Reallocated_Event_Count':
        type(self).ReallocatedEventCount.Set(self, value)
      elif attribute == 'Reallocated_Sector_Ct':
        type(self).ReallocatedSectorsCount.Set(self, value)
      elif attribute == 'Run_Out_Cancel':
        type(self).RunOutCancel.Set(self, value)
      elif attribute == 'Seek_Error_Rate':
        type(self).SeekErrorRate.Set(self, value)
      elif attribute == 'Seek_Time_Performance':
        type(self).SeekTimePerformance.Set(self, value)
      elif attribute == 'Shock_Count_Write_Opern':
        type(self).ShockCountWriteOperation.Set(self, value)
      elif attribute == 'Shock_Rate_Write_Opern':
        type(self).ShockRateWriteOperation.Set(self, value)
      elif attribute == 'Soft_Read_Error_Rate':
        type(self).SoftReadErrorRate.Set(self, value)
      elif attribute == 'Spin_Buzz':
        type(self).SpinBuzz.Set(self, value)
      elif attribute == 'Spin_High_Current':
        type(self).SpinHighCurrent.Set(self, value)
      elif attribute == 'Spin_Retry_Count':
        type(self).SpinRetryCount.Set(self, value)
      elif attribute == 'Spin_Up_Time':
        type(self).SpinUpTimeLatest.Set(self, value)
        average = _IntOrNegativeOne(result, 'average')
        type(self).SpinUpTime.Set(self, average)
      elif attribute == 'Start_Stop_Count':
        type(self).StartStopCount.Set(self, value)
      elif attribute == 'TA_Increase_Count':
        type(self).TaIncreaseCount.Set(self, value)
      elif attribute == 'Temperature_Celsius':
        type(self).TemperatureCelsius.Set(self, value)
        type(self).TemperatureCelsiusMin.Set(
            self, _IntOrNegativeOne(result, 'min'))
        type(self).TemperatureCelsiusMax.Set(
            self, _IntOrNegativeOne(result, 'max'))
      elif attribute == 'Throughput_Performance':
        type(self).ThroughputPerformance.Set(self, value)
      elif attribute == 'UDMA_CRC_Error_Count':
        type(self).UdmaCrcErrorCount.Set(self, value)


class FlashSubVolUbiLinux26(BASESTORAGE.X_CATAWAMPUS_ORG_FlashMedia.SubVolume):
  """Catawampus Storage Flash SubVolume implementation for UBI volumes."""

  def __init__(self, ubivol):
    super(FlashSubVolUbiLinux26, self).__init__()
    self.ubivol = ubivol

  @property
  def DataMBytes(self):
    bytesiz = IntFromFile(os.path.join(SYS_UBI, self.ubivol, 'data_bytes'))
    return int(bytesiz / 1024 / 1024)

  @property
  def Name(self):
    return _ReadOneLine(os.path.join(SYS_UBI, self.ubivol, 'name'), self.ubivol)

  @property
  def Status(self):
    corr = IntFromFile(os.path.join(SYS_UBI, self.ubivol, 'corrupted'))
    return 'OK' if corr == 0 else 'Corrupted'


class FlashMediumUbiLinux26(BASESTORAGE.X_CATAWAMPUS_ORG_FlashMedia):
  """Catawampus Storage FlashMedium implementation for UBI volumes."""

  Name = tr.types.ReadOnlyString('')

  def __init__(self, ubiname):
    super(FlashMediumUbiLinux26, self).__init__()
    type(self).Name.Set(self, ubiname)
    self.SubVolumeList = {}
    num = 0
    for i in range(128):
      subvolname = self.Name + '_' + str(i)
      try:
        if os.stat(os.path.join(SYS_UBI, self.Name, subvolname)):
          self.SubVolumeList[str(num)] = FlashSubVolUbiLinux26(subvolname)
          num += 1
      except OSError:
        pass

  @property
  def BadEraseBlocks(self):
    return IntFromFile(os.path.join(SYS_UBI, self.Name, 'bad_peb_count'))

  @property
  def CorrectedErrors(self):
    mtdnum = IntFromFile(os.path.join(SYS_UBI, self.Name, 'mtd_num'))
    try:
      ecc = GETMTDSTATS(os.path.join(SLASHDEV, 'mtd' + str(mtdnum)))
      return int(ecc.corrected)
    except IOError as e:
      print 'WARN: GetMtdStats: %s' % e
      return -1

  @property
  def EraseBlockSize(self):
    return IntFromFile(os.path.join(SYS_UBI, self.Name, 'eraseblock_size'))

  @property
  def IOSize(self):
    return IntFromFile(os.path.join(SYS_UBI, self.Name, 'min_io_size'))

  @property
  def MaxEraseCount(self):
    return IntFromFile(os.path.join(SYS_UBI, self.Name, 'max_ec'))

  @property
  def SubVolumeNumberOfEntries(self):
    return len(self.SubVolumeList)

  @property
  def ReservedEraseBlocks(self):
    return IntFromFile(os.path.join(SYS_UBI, self.Name, 'reserved_for_bad'))

  @property
  def TotalEraseBlocks(self):
    return IntFromFile(os.path.join(SYS_UBI, self.Name, 'total_eraseblocks'))

  @property
  def UncorrectedErrors(self):
    mtdnum = IntFromFile(os.path.join(SYS_UBI, self.Name, 'mtd_num'))
    try:
      ecc = GETMTDSTATS(os.path.join(SLASHDEV, 'mtd' + str(mtdnum)))
      return int(ecc.failed)
    except IOError as e:
      print 'WARN: GetMtdStats: %s' % e
      return -1


class DrivePerformance(PHYSICALMEDIUM.X_CATAWAMPUS_ORG_DrivePerformance):
  """Catawampus Storage Drive Performance implementation."""

  IoInProgress = tr.types.ReadOnlyUnsigned(0)
  IoMilliseconds = tr.types.ReadOnlyUnsigned(0)
  ReadMilliseconds = tr.types.ReadOnlyUnsigned(0)
  ReadSectors = tr.types.ReadOnlyUnsigned(0)
  ReadsCompleted = tr.types.ReadOnlyUnsigned(0)
  ReadsMerged = tr.types.ReadOnlyUnsigned(0)
  WeightedIoMilliseconds = tr.types.ReadOnlyUnsigned(0)
  WriteMilliseconds = tr.types.ReadOnlyUnsigned(0)
  WriteSectors = tr.types.ReadOnlyUnsigned(0)
  WritesCompleted = tr.types.ReadOnlyUnsigned(0)
  WritesMerged = tr.types.ReadOnlyUnsigned(0)

  def __init__(self, dev):
    super(DrivePerformance, self).__init__()
    filename = DISKSTAT + dev + '/stat'
    with open(filename) as f:
      fields = f.readline().split()
      if len(fields) >= 11:
        type(self).ReadsCompleted.Set(self, long(fields[0]))
        type(self).ReadsMerged.Set(self, long(fields[1]))
        type(self).ReadSectors.Set(self, long(fields[2]))
        type(self).ReadMilliseconds.Set(self, long(fields[3]))
        type(self).WritesCompleted.Set(self, long(fields[4]))
        type(self).WritesMerged.Set(self, long(fields[5]))
        type(self).WriteSectors.Set(self, long(fields[6]))
        type(self).WriteMilliseconds.Set(self, long(fields[7]))
        type(self).IoInProgress.Set(self, long(fields[8]))
        type(self).IoMilliseconds.Set(self, long(fields[9]))
        type(self).WeightedIoMilliseconds.Set(self, long(fields[10]))


class SataPHY(PHYSICALMEDIUM.X_CATAWAMPUS_ORG_SataPHY):
  """Catawampus Storage SATA PHY counters implementation."""

  CmdFailedICRC = tr.types.ReadOnlyInt(-1)
  DeviceToHostNonDataRetries = tr.types.ReadOnlyInt(-1)
  HostToDeviceCrcErrors = tr.types.ReadOnlyInt(-1)
  HostToDeviceNonCrcErrors = tr.types.ReadOnlyInt(-1)
  PhyRdyToPhyNRdy = tr.types.ReadOnlyInt(-1)
  RErrDataFis = tr.types.ReadOnlyInt(-1)
  RErrDeviceToHostDataFis = tr.types.ReadOnlyInt(-1)
  RErrDeviceToHostNonDataFis = tr.types.ReadOnlyInt(-1)
  RErrHostToDeviceDataFis = tr.types.ReadOnlyInt(-1)
  RErrHostToDeviceDataFisCrc = tr.types.ReadOnlyInt(-1)
  RErrHostToDeviceDataFisNonCrc = tr.types.ReadOnlyInt(-1)
  RErrHostToDeviceNonDataFis = tr.types.ReadOnlyInt(-1)
  RErrHostToDeviceNonDataFisCrc = tr.types.ReadOnlyInt(-1)
  RErrHostToDeviceNonDataFisNonCrc = tr.types.ReadOnlyInt(-1)
  RErrNonDataFis = tr.types.ReadOnlyInt(-1)
  RegisterFisComreset = tr.types.ReadOnlyInt(-1)

  def __init__(self, dev):
    super(SataPHY, self).__init__()
    self.dev = dev
    self._ParseSmartctlSataphy()

  def _ParseSmartctlSataphy(self):
    dev = SLASHDEV + self.dev
    smart = subprocess.Popen([SMARTCTL, '--log=sataphy', dev],
                             stdout=subprocess.PIPE)
    out, _ = smart.communicate(None)
    for line in out.splitlines():
      result = SATAPHY.search(line)
      if result is None:
        continue
      reg = _IntOrNegativeOne(result, 'reg')
      val = _IntOrNegativeOne(result, 'val')
      if reg == 1:
        type(self).CmdFailedICRC.Set(self, val)
      elif reg == 2:
        type(self).RErrDataFis.Set(self, val)
      elif reg == 3:
        type(self).RErrDeviceToHostDataFis.Set(self, val)
      elif reg == 4:
        type(self).RErrHostToDeviceDataFis.Set(self, val)
      elif reg == 5:
        type(self).RErrNonDataFis.Set(self, val)
      elif reg == 6:
        type(self).RErrDeviceToHostNonDataFis.Set(self, val)
      elif reg == 7:
        type(self).RErrHostToDeviceNonDataFis.Set(self, val)
      elif reg == 8:
        type(self).DeviceToHostNonDataRetries.Set(self, val)
      elif reg == 9:
        type(self).PhyRdyToPhyNRdy.Set(self, val)
      elif reg == 10:
        type(self).RegisterFisComreset.Set(self, val)
      elif reg == 11:
        type(self).HostToDeviceCrcErrors.Set(self, val)
      elif reg == 13:
        type(self).HostToDeviceNonCrcErrors.Set(self, val)
      elif reg == 15:
        type(self).RErrHostToDeviceDataFisCrc.Set(self, val)
      elif reg == 16:
        type(self).RErrHostToDeviceDataFisNonCrc.Set(self, val)
      elif reg == 18:
        type(self).RErrHostToDeviceNonDataFisCrc.Set(self, val)
      elif reg == 19:
        type(self).RErrHostToDeviceNonDataFisNonCrc.Set(self, val)


class CapabilitiesNoneLinux26(BASESTORAGE.Capabilities):
  """Trivial tr-140 StorageService.Capabilities, all False."""

  FTPCapable = tr.types.ReadOnlyBool(False)
  HTTPCapable = tr.types.ReadOnlyBool(False)
  HTTPSCapable = tr.types.ReadOnlyBool(False)
  HTTPWritable = tr.types.ReadOnlyBool(False)
  SFTPCapable = tr.types.ReadOnlyBool(False)
  SupportedNetworkProtocols = tr.types.ReadOnlyString('')
  SupportedRaidTypes = tr.types.ReadOnlyString('')
  VolumeEncryptionCapable = tr.types.ReadOnlyBool(False)

  @property
  def SupportedFileSystemTypes(self):
    """Returns possible filesystems.

    Parses /proc/filesystems, omit any defined as uninteresting in
    _IsSillyFileSystem(), and return the rest.

    Returns:
      a string of comma-separated filesystem types.
    """
    fslist = set()
    with open(PROC_FILESYSTEMS) as f:
      for line in f:
        line = line.strip()
        split_line = line.split('\t')
        devtype = None
        if len(split_line) == 2:
          devtype = split_line[0]
          fstype = split_line[1]
        else:
          fstype = split_line[0]
        # Rule of thumb to skip internal, non-interesting filesystems,
        # except for tmpfs which is allowed.
        if devtype == 'nodev' and fstype != 'tmpfs':
          continue
        if _IsSillyFilesystem(fstype):
          continue
        fslist.add(_FsType(fstype))
    return ','.join(sorted(fslist, key=str.lower))


class StorageServiceLinux26(BASESTORAGE):
  """Implements a basic tr-140 for Linux 2.6-ish systems.

  This class implements no network file services, it only exports
  the LogicalVolume information.
  """

  # TODO(dgentry): tr-140 says this is supposed to be writable
  Enable = tr.types.ReadOnlyBool(True)

  def __init__(self):
    super(StorageServiceLinux26, self).__init__()
    self.Capabilities = CapabilitiesNoneLinux26()
    self.Unexport('Alias')
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
    self.X_CATAWAMPUS_ORG_FlashMediaList = {}

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

  @property
  def X_CATAWAMPUS_ORG_FlashMediaNumberOfEntries(self):
    return len(self.X_CATAWAMPUS_ORG_FlashMediaList)

  def _ParseProcMounts(self):
    """Return list of (mount point, filesystem type) tuples."""
    mounts = dict()
    try:
      with open(PROC_MOUNTS) as f:
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
    except IOError:
      return []
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

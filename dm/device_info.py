#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-181 Device.DeviceInfo object.

Handles the Device.DeviceInfo portion of TR-181, as described
by http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import abc
import glob
import os
import tr.core
import tr.tr098_v1_2
import tr.tr181_v2_2

BASE98IGD = tr.tr098_v1_2.InternetGatewayDevice_v1_4.InternetGatewayDevice
BASE181DEVICE = tr.tr181_v2_2.Device_v2_2

# Unit tests can override these with fake data
PROC_MEMINFO = '/proc/meminfo'
PROC_NET_DEV = '/proc/net/dev'
PROC_UPTIME = '/proc/uptime'
SLASH_PROC = '/proc'


class DeviceIdMeta(object):
  """Class to provide platform-specific fields for DeviceInfo.

  Each platform is expected to subclass DeviceIdMeta and supply concrete
  implementations of all methods. We use a Python Abstract Base Class
  to protect against future versions. If we add fields to this class,
  any existing platform implementations will be prompted to add implementations
  (because they will fail to startup when their DeviceId fails to
  instantiate.
  """
  __metaclass__ = abc.ABCMeta

  @abc.abstractproperty
  def Manufacturer(self):
    return None

  @abc.abstractproperty
  def ManufacturerOUI(self):
    return None

  @abc.abstractproperty
  def ModelName(self):
    return None

  @abc.abstractproperty
  def Description(self):
    return None

  @abc.abstractproperty
  def SerialNumber(self):
    return None

  @abc.abstractproperty
  def HardwareVersion(self):
    return None

  @abc.abstractproperty
  def AdditionalHardwareVersion(self):
    return None

  @abc.abstractproperty
  def SoftwareVersion(self):
    return None

  @abc.abstractproperty
  def AdditionalSoftwareVersion(self):
    return None

  @abc.abstractproperty
  def ProductClass(self):
    return None

  @abc.abstractproperty
  def ModemFirmwareVersion(self):
    return None


def _GetUptime():
  """Return a string of the number of integer seconds since boot."""
  try:
    uptime = float(open(PROC_UPTIME).read().split()[0])
  except IOError:
    # TODO(dgentry) - LOG the exception, but return zeros by default
    uptime = 0.0
  return str(int(uptime))


#pylint: disable-msg=W0231
class DeviceInfo181Linux26(BASE181DEVICE.DeviceInfo):
  """Implements tr-181 DeviceInfo for Linux 2.6 and similar systems."""

  def __init__(self, device_id):
    BASE181DEVICE.DeviceInfo.__init__(self)
    assert isinstance(device_id, DeviceIdMeta)
    self._device_id = device_id
    self.MemoryStatus = MemoryStatusLinux26()
    self.ProcessStatus = ProcessStatusLinux26()
    self.ProvisioningCode = None  # TODO(apenwarr): fill me
    self.FirstUseDate = None  # TODO(apenwarr): fill me
    self.NetworkProperties = self.NetworkProperties()
    self.NetworkProperties.MaxTCPWindowSize = 0,   # TODO(apenwarr): fill me
    self.NetworkProperties.TCPImplementation = ''  # TODO(apenwarr): fill me
    self.TemperatureStatus = self.TemperatureStatus()
    self.TemperatureStatus.TemperatureSensorNumberOfEntries = 0
    self.TemperatureStatus.TemperatureSensorList = {}
    self.VendorLogFileList = {}
    self.VendorConfigFileList = {}
    self.SupportedDataModelList = {}
    self.ProcessorList = {}

  def __getattr__(self, name):
    """Allows passthrough of parameters to the platform-supplied device_id."""
    if hasattr(self._device_id, name):
      return getattr(self._device_id, name)
    else:
      raise AttributeError

  @property
  def UpTime(self):
    return _GetUptime()

  @property
  def VendorLogFileNumberOfEntries(self):
    return len(self.VendorLogFileList)

  @property
  def VendorConfigFileNumberOfEntries(self):
    return len(self.VendorConfigFileList)

  @property
  def ProcessorNumberOfEntries(self):
    return len(self.ProcessorList)

  @property
  def SupportedDataModelNumberOfEntries(self):
    return len(self.SupportedDataModelList)


class MemoryStatusLinux26(BASE181DEVICE.DeviceInfo.MemoryStatus):
  """Abstraction to get memory information from the underlying platform.

  Reads /proc/meminfo to find TotalMem and FreeMem.
  """

  def __init__(self):
    BASE181DEVICE.DeviceInfo.MemoryStatus.__init__(self)
    (self._totalmem, self._freemem) = self._GetMemInfo()

  @property
  def Total(self):
    return self._totalmem

  @property
  def Free(self):
    return self._freemem

  def _GetMemInfo(self):
    """Fetch TotalMem and FreeMem from the underlying platform.

    Returns:
      a list of two integers, (totalmem, freemem)
    """
    totalmem = 0
    freemem = 0
    try:
      pfile = open(PROC_MEMINFO)
      for line in pfile:
        fields = line.split()
        name = fields[0]
        value = fields[1]
        if name == 'MemTotal:':
          totalmem = int(value)
        elif name == 'MemFree:':
          freemem = int(value)
    except IOError:
      # TODO(dgentry): LOG the exception, but return zeros by default
      pass
    return (totalmem, freemem)


class ProcessStatusLinux26(BASE181DEVICE.DeviceInfo.ProcessStatus):
  """Get information about running processes on Linux 2.6.

  Reads /proc/<pid> to get information about processes.
  """
  # Field ordering in /proc/<pid>/stat
  _PID = 0
  _COMM = 1
  _STATE = 2
  _UTIME = 13
  _STIME = 14
  _PRIO = 17
  _RSS = 23

  def __init__(self):
    BASE181DEVICE.DeviceInfo.ProcessStatus.__init__(self)
    tick = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
    self._msec_per_jiffy = 1000 / tick
    self.ProcessList = tr.core.AutoDict('ProcessList',
                                        iteritems=self.IterProcesses,
                                        getitem=self.GetProcess)

  def _LinuxStateToTr181(self, linux_state):
    """Maps Linux process states to TR-181 process state names.

    Args:
      linux_state: One letter describing the state of the linux process,
        as described in proc(5). One of "RSDZTW"

    Returns:
      the tr-181 string describing the process state.
    """
    mapping = {
        'R': 'Running',
        'S': 'Sleeping',
        'D': 'Uninterruptible',
        'Z': 'Zombie',
        'T': 'Stopped',
        'W': 'Uninterruptible'}
    return mapping.get(linux_state, 'Sleeping')

  def _JiffiesToMsec(self, utime, stime):
    ticks = int(utime) + int(stime)
    msecs = ticks * self._msec_per_jiffy
    return str(msecs)

  def _RemoveParens(self, command):
    return command[1:-1]

  def _ProcFileName(self, pid):
    return '%s/%s/stat' % (SLASH_PROC, pid)

  @property
  def CPUUsage(self):
    return 0   # TODO(apenwarr): figure out what this should do

  @property
  def ProcessNumberOfEntries(self):
    return len(self.ProcessList)

  def GetProcess(self, pid):
    """Get a self.Process() object for the given pid."""
    try:
      f = open(self._ProcFileName(pid))
    except IOError:
      raise KeyError(pid)
    fields = f.read().split()
    p = self.Process(PID=fields[self._PID],
                     Command=self._RemoveParens(fields[self._COMM]),
                     Size=fields[self._RSS],
                     Priority=fields[self._PRIO],
                     CPUTime=self._JiffiesToMsec(fields[self._UTIME],
                                                 fields[self._STIME]),
                     State=self._LinuxStateToTr181(fields[self._STATE]))
    p.ValidateExports()
    return p

  def IterProcesses(self):
    """Walks through /proc/<pid>/stat to return a list of all processes."""
    for filename in glob.glob(self._ProcFileName('[0123456789]*')):
      pid = int(filename.split('/')[-2])
      try:
        proc = self.GetProcess(pid)
      except KeyError:
        # This isn't an error. We have a list of files which existed the
        # moment the glob.glob was run. If a process exits before we get
        # around to reading it, its /proc files will go away.
        continue
      yield pid, proc


class DeviceInfo98Linux26(BASE98IGD.DeviceInfo):
  """Implementation of tr-98 DeviceInfo for Linux."""

  def __init__(self, device_id):
    BASE98IGD.DeviceInfo.__init__(self)
    assert isinstance(device_id, DeviceIdMeta)
    self._device_id = device_id
    self.Unexport(params='DeviceLog')
    self.Unexport(params='EnabledOptions')
    self.Unexport(params='FirstUseDate')
    self.Unexport(params='ProvisioningCode')
    self.Unexport(params='SpecVersion')
    self.Unexport(lists='VendorConfigFile')
    self.VendorConfigFileNumberOfEntries = 0

  @property
  def UpTime(self):
    return _GetUptime()

  def __getattr__(self, name):
    if hasattr(self._device_id, name):
      return getattr(self._device_id, name)
    else:
      raise AttributeError


def main():
  dp = DeviceInfo181Linux26()
  #print tr.core.DumpSchema(dp)
  print tr.core.Dump(dp)

if __name__ == '__main__':
  main()
